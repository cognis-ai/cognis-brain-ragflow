"""Cognis Knowledge — Clerk JWT validator for RAGFlow.

Mirrors cognis-concierge/letta/server/rest_api/middleware/cognis_auth.py
but adapted for RAGFlow's Flask stack (no FastAPI dependency injection).

Verifies a Clerk-issued JWT presented via ``Authorization: Bearer <jwt>``,
maps the JWT's ``org_id`` claim to a RAGFlow ``Tenant.id`` row by querying
Bridge's ``GET /v1/tenants/{cognisOrgId}`` endpoint, and stashes the
resolved IDs on ``flask.g`` for downstream blueprints.

Configuration (env):
    JWT_PUBLIC_KEY_URL   Clerk JWKS URL
    JWT_ISSUER           (optional) expected `iss` claim
    JWT_AUDIENCE         (optional) expected `aud` claim
    COGNIS_BRIDGE_URL    Bridge resolver URL (for org→tenant lookup)

If ``JWT_PUBLIC_KEY_URL`` is not set, the dependency is a no-op pass-through
(local dev preserves upstream RAGFlow's own auth flow).

Implementation: stdlib + cryptography + requests (RAGFlow already depends
on all three). No new pip install needed.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from typing import Any, Optional

import requests
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.hashes import SHA256, SHA384, SHA512
from flask import Flask, g, jsonify, request

logger = logging.getLogger(__name__)

_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_CACHE_TTL_SECONDS = 600
_JWKS_LOCK = threading.Lock()

_HASH_ALGORITHMS = {"RS256": SHA256(), "RS384": SHA384(), "RS512": SHA512()}


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _fetch_jwks(jwks_url: str) -> dict[str, Any]:
    now = time.time()
    with _JWKS_LOCK:
        if (
            _JWKS_CACHE["keys"] is not None
            and now - _JWKS_CACHE["fetched_at"] < _JWKS_CACHE_TTL_SECONDS
        ):
            return _JWKS_CACHE["keys"]
        try:
            response = requests.get(jwks_url, timeout=5.0)
            response.raise_for_status()
            jwks = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch Clerk JWKS from %s: %s", jwks_url, exc)
            raise RuntimeError("Auth service unavailable") from exc
        _JWKS_CACHE["keys"] = jwks
        _JWKS_CACHE["fetched_at"] = now
        return jwks


def _public_key_from_jwk(jwk: dict[str, Any]):
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

    n = int.from_bytes(_b64url_decode(jwk["n"]), "big")
    e = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    return RSAPublicNumbers(e, n).public_key()


def _verify_jwt(token: str, jwks_url: str, audience: Optional[str], issuer: Optional[str]) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed JWT")
    header_raw, payload_raw, signature_raw = parts
    header = json.loads(_b64url_decode(header_raw))
    payload = json.loads(_b64url_decode(payload_raw))
    alg = header.get("alg")
    if alg not in _HASH_ALGORITHMS:
        raise ValueError(f"unsupported alg {alg}")
    kid = header.get("kid")

    jwks = _fetch_jwks(jwks_url)
    matching = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if matching is None:
        # JWKS rotation race — re-fetch once
        _JWKS_CACHE["keys"] = None
        jwks = _fetch_jwks(jwks_url)
        matching = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if matching is None:
            raise ValueError(f"no JWK matching kid {kid}")

    public_key = _public_key_from_jwk(matching)
    signing_input = f"{header_raw}.{payload_raw}".encode("utf-8")
    signature = _b64url_decode(signature_raw)

    try:
        public_key.verify(signature, signing_input, PKCS1v15(), _HASH_ALGORITHMS[alg])
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"signature verification failed: {exc}") from exc

    now = int(time.time())
    if "exp" in payload and now > payload["exp"]:
        raise ValueError("token expired")
    if "nbf" in payload and now < payload["nbf"]:
        raise ValueError("token not yet valid")
    if audience and payload.get("aud") != audience:
        raise ValueError(f"audience mismatch: {payload.get('aud')!r} != {audience!r}")
    if issuer and payload.get("iss") != issuer:
        raise ValueError(f"issuer mismatch: {payload.get('iss')!r} != {issuer!r}")

    return payload


def _resolve_org_to_tenant_via_bridge(cognis_org_id: str) -> Optional[str]:
    bridge_url = os.environ.get("COGNIS_BRIDGE_URL", "").strip()
    if not bridge_url:
        return None
    try:
        # GET is public + idempotent; Bridge exposes the org_mappings rows
        # via /v1/tenants/{orgId}. Use the bot-token-equivalent admin key
        # if available; otherwise the call uses no auth and Bridge will
        # 401 — which is fine, the dependency falls through to RAGFlow's
        # own auth in that case.
        admin_key = os.environ.get("COGNIS_BRIDGE_ADMIN_KEY", "").strip()
        headers = {"Authorization": f"Bearer {admin_key}"} if admin_key else {}
        url = f"{bridge_url.rstrip('/')}/v1/tenants/{cognis_org_id}"
        resp = requests.get(url, headers=headers, timeout=5.0)
        if resp.status_code != 200:
            return None
        rows = resp.json()
        for row in rows if isinstance(rows, list) else []:
            if row.get("product") == "knowledge" and row.get("status") == "active":
                return str(row.get("nativeTenantId", "")) or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bridge org→tenant lookup failed: %s", exc)
    return None


def register_cognis_auth(app: Flask) -> None:
    """Install the Cognis Clerk-JWT before_request hook on the Flask app.

    Skips entirely when JWT_PUBLIC_KEY_URL is unset (preserves upstream
    auth in local dev / parity-mode). Otherwise: validates Clerk JWT,
    populates ``flask.g`` with ``cognis_org_id`` + ``ragflow_tenant_id``,
    then lets the request proceed to RAGFlow's own routing.

    On invalid token → 401. On missing tenant mapping → falls through
    (returns 200 from RAGFlow's own auth or 401 if RAGFlow requires
    its own session — caller picks).
    """
    jwks_url = os.environ.get("JWT_PUBLIC_KEY_URL", "").strip()
    if not jwks_url:
        logger.info("Cognis auth disabled (JWT_PUBLIC_KEY_URL unset) — passthrough")
        return

    audience = os.environ.get("JWT_AUDIENCE", "").strip() or None
    issuer = os.environ.get("JWT_ISSUER", "").strip() or None

    @app.before_request
    def cognis_auth_hook() -> Optional[Any]:
        auth = request.headers.get("Authorization", "").strip()
        if not auth.startswith("Bearer "):
            # No Cognis JWT — let RAGFlow's own auth take it.
            return None
        token = auth[len("Bearer ") :]
        try:
            claims = _verify_jwt(token, jwks_url, audience, issuer)
        except ValueError as err:
            return jsonify({"code": 401, "message": f"Cognis auth failed: {err}"}), 401
        cognis_org_id = claims.get("org_id")
        if not cognis_org_id:
            return None  # JWT valid but no org context — fall through
        tenant_id = _resolve_org_to_tenant_via_bridge(cognis_org_id)
        g.cognis_org_id = cognis_org_id
        g.cognis_user_sub = claims.get("sub")
        g.cognis_user_email = claims.get("email")
        g.ragflow_tenant_id = tenant_id
        return None

    logger.info("Cognis auth registered on Flask app (jwks_url=%s)", jwks_url)
