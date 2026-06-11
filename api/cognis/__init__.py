"""Cognis Knowledge — productization surface for the cognis-brain-ragflow fork.

Cognis-specific code only — everything else under ``api/`` is upstream
RAGFlow, untouched. Contract:

- ``cognis_auth.register_cognis_auth`` — Quart ``before_request`` hook
  (RAGFlow's app is Quart, not FastAPI like cognis-concierge) that
  verifies a Clerk JWT presented via ``Authorization: Bearer <jwt>`` and
  maps the ``org_id`` claim to a RAGFlow ``Tenant.id`` row through Bridge.
  Deny-by-default with an explicit public-route allowlist (SEC-5).
- ``branding`` — env-driven Cognis brand strings for the web UI rebrand
  (loaded by ``web/src/branding/``).

Mounted from upstream's ``ragflow_server.py`` (Gate-1 defect 5; one of the
fork's three upstream-file touches, logged in FORK.md):
    from api.cognis.cognis_auth import register_cognis_auth
    register_cognis_auth(app)

v1.5 will promote this to a proper middleware once we add a Clerk-org /
RAGFlow-tenant join table directly in MySQL.
"""

__all__ = ["cognis_auth", "branding"]
