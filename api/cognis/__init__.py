"""Cognis Knowledge — productization surface for the cognis-brain-ragflow fork.

Cognis-specific code only — everything else under ``api/`` is upstream
RAGFlow, untouched. Contract:

- ``cognis_auth.cognis_auth_dependency`` — Flask blueprint helper (RAGFlow
  uses Flask, not FastAPI like cognis-concierge) that verifies a Clerk JWT
  presented via ``Authorization: Bearer <jwt>`` and maps the ``org_id``
  claim to a RAGFlow ``Tenant.id`` row through Bridge.
- ``branding`` — env-driven Cognis brand strings for the web UI rebrand
  (loaded by ``web/src/branding/``).

Mounted from upstream's ``ragflow_server.py`` by adding ONE line:
    from api.cognis.cognis_auth import register_cognis_auth
    register_cognis_auth(app)

That's the only fork-touch on an upstream Python file. v1.5 will promote
this to a proper Flask middleware once we add a Clerk-org / RAGFlow-tenant
join table directly in MySQL.
"""

__all__ = ["cognis_auth", "branding"]
