#
#  Copyright 2026 Cognis AI. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""Unit tests for the Cognis Clerk-JWT hook (api/cognis/cognis_auth.py).

Covers the SEC-5 deny-by-default contract:
- hook is a no-op when JWT_PUBLIC_KEY_URL is unset (Pattern A passthrough)
- anonymous requests are denied (401) except on the public-route allowlist
- non-Clerk credentials (native session / API token / Bridge admin key)
  fall through to RAGFlow's own auth
- invalid Clerk JWT -> 401; valid JWT without org or tenant mapping -> 403
- valid JWT with an active mapping populates quart.g and proceeds
"""

import asyncio
import base64
import json

import pytest

quart = pytest.importorskip("quart")

from api.cognis import cognis_auth  # noqa: E402

JWKS_URL = "https://clerk.example.test/.well-known/jwks.json"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _fake_clerk_jwt(payload: dict) -> str:
    header = _b64url(json.dumps({"alg": "RS256", "kid": "k1"}).encode())
    body = _b64url(json.dumps(payload).encode())
    return f"{header}.{body}.{_b64url(b'sig')}"


def _fake_itsdangerous_token() -> str:
    # itsdangerous URLSafeTimedSerializer output is dot-separated too, but
    # its first segment decodes to a JSON *string*, not a JWS header object.
    return f"{_b64url(json.dumps('some-access-token').encode())}.aGVsbG8.c2ln"


def _make_app(monkeypatch, *, jwks_url: str = JWKS_URL) -> "quart.Quart":
    if jwks_url:
        monkeypatch.setenv("JWT_PUBLIC_KEY_URL", jwks_url)
    else:
        monkeypatch.delenv("JWT_PUBLIC_KEY_URL", raising=False)
    monkeypatch.delenv("JWT_AUDIENCE", raising=False)
    monkeypatch.delenv("JWT_ISSUER", raising=False)

    app = quart.Quart(__name__)

    @app.route("/api/v1/protected")
    async def protected():
        return {
            "ok": True,
            "org": getattr(quart.g, "cognis_org_id", None),
            "tenant": getattr(quart.g, "ragflow_tenant_id", None),
        }

    @app.route("/api/v1/auth/login")
    async def login():
        return {"ok": True}

    @app.route("/api/v1/system/healthz")
    async def healthz():
        return {"ok": True}

    @app.route("/api/v1/chatbots/abc/info")
    async def chatbot_info():
        return {"ok": True}

    cognis_auth.register_cognis_auth(app)
    return app


def _get(app, path, headers=None):
    async def _go():
        client = app.test_client()
        response = await client.get(path, headers=headers or {})
        return response.status_code, await response.get_json()

    return asyncio.run(_go())


def test_passthrough_when_jwks_url_unset(monkeypatch):
    app = _make_app(monkeypatch, jwks_url="")
    status, body = _get(app, "/api/v1/protected")
    assert status == 200
    assert body["ok"] is True


def test_anonymous_denied_on_protected_route(monkeypatch):
    app = _make_app(monkeypatch)
    status, body = _get(app, "/api/v1/protected")
    assert status == 401
    assert body["code"] == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/login",
        "/api/v1/system/healthz",
        "/api/v1/chatbots/abc/info",
    ],
)
def test_anonymous_allowed_on_public_allowlist(monkeypatch, path):
    app = _make_app(monkeypatch)
    status, body = _get(app, path)
    assert status == 200
    assert body["ok"] is True


def test_native_credential_falls_through(monkeypatch):
    app = _make_app(monkeypatch)
    status, _ = _get(app, "/api/v1/protected", headers={"Authorization": "Bearer ragflow-admin-key"})
    assert status == 200


def test_itsdangerous_token_falls_through(monkeypatch):
    app = _make_app(monkeypatch)
    status, _ = _get(app, "/api/v1/protected", headers={"Authorization": _fake_itsdangerous_token()})
    assert status == 200


def test_invalid_clerk_jwt_is_denied(monkeypatch):
    app = _make_app(monkeypatch)

    def _reject(token, jwks_url, audience, issuer):
        raise ValueError("signature verification failed")

    monkeypatch.setattr(cognis_auth, "_verify_jwt", _reject)
    token = _fake_clerk_jwt({"org_id": "org_1"})
    status, body = _get(app, "/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert status == 401
    assert "Cognis auth failed" in body["message"]


def test_valid_jwt_without_org_is_403(monkeypatch):
    app = _make_app(monkeypatch)
    monkeypatch.setattr(cognis_auth, "_verify_jwt", lambda token, jwks_url, audience, issuer: {"sub": "user_1"})
    token = _fake_clerk_jwt({"sub": "user_1"})
    status, body = _get(app, "/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert status == 403
    assert "no org context" in body["message"]


def test_valid_jwt_without_tenant_mapping_is_403(monkeypatch):
    app = _make_app(monkeypatch)
    monkeypatch.setattr(cognis_auth, "_verify_jwt", lambda token, jwks_url, audience, issuer: {"org_id": "org_1"})
    monkeypatch.setattr(cognis_auth, "_resolve_org_to_tenant_via_bridge", lambda org_id: None)
    token = _fake_clerk_jwt({"org_id": "org_1"})
    status, body = _get(app, "/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert status == 403
    assert "No active Cognis Knowledge tenant" in body["message"]


def test_valid_jwt_with_mapping_passes_and_populates_g(monkeypatch):
    app = _make_app(monkeypatch)
    claims = {"org_id": "org_1", "sub": "user_1", "email": "user@example.test"}
    monkeypatch.setattr(cognis_auth, "_verify_jwt", lambda token, jwks_url, audience, issuer: claims)
    monkeypatch.setattr(cognis_auth, "_resolve_org_to_tenant_via_bridge", lambda org_id: "tenant_42")
    token = _fake_clerk_jwt(claims)
    status, body = _get(app, "/api/v1/protected", headers={"Authorization": f"Bearer {token}"})
    assert status == 200
    assert body["org"] == "org_1"
    assert body["tenant"] == "tenant_42"


def test_clerk_jwt_detector():
    assert cognis_auth._looks_like_clerk_jwt(_fake_clerk_jwt({"org_id": "x"}))
    assert not cognis_auth._looks_like_clerk_jwt(_fake_itsdangerous_token())
    assert not cognis_auth._looks_like_clerk_jwt("ragflow-admin-key")
    assert not cognis_auth._looks_like_clerk_jwt("a.b")
