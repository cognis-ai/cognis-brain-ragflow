# Cognis Knowledge

Answers questions from your documents.

Cognis Knowledge is the document-Q&A product of the Cognis platform — you upload PDFs, HTML, knowledge bases, internal docs; it embeds them, indexes them, and answers questions with citations across them. Every other Cognis product can pull from it (Support replies citing your docs, Concierge remembers what's in them, etc.).

## What this repo is

A soft fork of [`infiniflow/ragflow`](https://github.com/infiniflow/ragflow) (Apache-2.0). RAGFlow already ships multi-tenancy (`Tenant` / `UserTenant` / `TenantLLM` ORM models) so the Cognis layer is minimal:

| File | Role |
|------|------|
| `api/cognis/cognis_auth.py`         | Flask `before_request` hook: validates Clerk JWT, maps `org_id` → RAGFlow tenant |
| `api/cognis/branding.py`            | Brand strings the web UI reads |
| `rag/llm/cognis_provider.py`        | Registers a "Cognis" LLM factory pointing at `llm.cognisai.com` |
| `Dockerfile.cognis`                 | Wires the hooks via entrypoint shim (no upstream source edits) |

Total fork-diff target: ≤3% of upstream LOC. Achieved: ~600 LOC added, 0 modified.

## Production runtime

RAGFlow needs MySQL + Elasticsearch + the RAGFlow Python service. Use the upstream docker-compose recipe with the Cognis image swapped in:

```bash
docker build -t ghcr.io/cognis-ai/knowledge:latest -f Dockerfile.cognis .
```

Cognis env to set:

```bash
COGNIS_BRIDGE_URL=https://bridge.cognisai.com
JWT_PUBLIC_KEY_URL=https://<your-clerk-frontend>/.well-known/jwks.json
COGNIS_LLM_GATEWAY=https://llm.cognisai.com/v1
COGNIS_BRANDING=on
```

Bridge env (cognis-platform):

```bash
RAGFLOW_ADMIN_BASE_URL=https://knowledge.cognisai.com
RAGFLOW_ADMIN_API_KEY=<the RAGFlow admin token>
RAGFLOW_PUBLIC_URL=https://knowledge.cognisai.com
```

Dev mode: leave the Bridge env vars unset — `RagflowAdminClient` runs in stub mode (returns synthetic IDs) so the whole Cognis platform runs locally without RAGFlow.

## License + support

Apache-2.0 throughout. Portal: <https://app.cognisai.com/dashboard/knowledge>. Support: <support@cognisai.com>.
