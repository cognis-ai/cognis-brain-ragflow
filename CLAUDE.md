# Cognis Brain RAGFlow — repo context for Claude

> **License posture (READ FIRST):** Upstream `infiniflow/ragflow` is plain Apache-2.0 at fork-bootstrap SHA `5e46457c28d615aec5f9676740c8408121cdcce7` (2026-05-12). NO Commons Clause, NO Sustainable Use rider, NO Elastic License addendum, no `enterprise/`/`ee/`/`cloud/`/`pro/`/`saas/` trap dirs. The doctrine had previously flagged "possible Commons Clause" — investigated and not present at this SHA. License-gate CI continues to enforce Apache-2.0 cleanliness on every PR and rebase. If you see a future upstream rebase introduce SSPL / BUSL / Commons Clause / FSL / PolyForm / AGPL / Elastic License headers, **STOP and escalate to platform-eng** — do not merge.

This is a soft fork of `infiniflow/ragflow`. **The fork is not the product — `cognis-platform/apps/bridge` is.** Every hour spent editing RAGFlow's Flask routers or Python services here costs 3× at next rebase. Cognis-specific code lives in Bridge; this repo holds branding, auth glue, and the LLM-provider swap.

## Role in the Cognis stack

`cognis-brain-ragflow` is the **document-ingestion + retrieval tier** of Cognis Brain (Phase 6). Brain is a platform-of-products tier offering private-LLM serving (`cognis-brain-vllm`), retrieval (this repo), and fine-tuning (`cognis-brain-axolotl`) to enterprise tenants. RAGFlow handles the RAG / context layer — deep document parsing (PDF, DOCX, OCR), chunking, embedding, hybrid retrieval (Elasticsearch / Infinity), and GraphRAG.

## Branches

- `cognis/main` — default. Cognis work.
- `vendor/upstream` — mirror of infiniflow/ragflow:main. NEVER edit.

## Hard rules

1. **License vigilance — see banner above.** Apache-2.0 only. License-gate CI is the safety net but you are the first line.
2. **Never `import openai` / `import anthropic` / `import cohere` / `import groq` / `import dashscope` directly.** Wrap everything via `@cognis/llm-client` (when called via Bridge) or, for in-process RAGFlow LLM provider plug-ins, the future `rag/llm/cognis_provider.py` (OpenAI-compatible client pinned at `llm.cognisai.com`). Upstream pulls in `anthropic==0.34.1`, `cohere==5.6.2`, `groq==0.9.0`, `mistralai==0.4.2`, `dashscope==1.25.11`, `zhipuai==2.0.1`, `voyageai==0.2.3`, `replicate==0.31.0`, `volcengine==1.0.194`, `qianfan==0.4.6`, `litellm~=1.82.0`, `ollama>=0.5.0` — they remain in `pyproject.toml` but Cognis-deployed instances must route via the proxy.
3. **No license traps to restore.** None exist at fork time. If upstream introduces `pro/`, `ee/`, `cloud/`, `saas/`, `platform/`, or `premium/` directories in a future rebase, strip in a SEPARATE commit before merging — never restore them. Note: `admin/` is upstream's own Flask admin pane (Apache-2.0) — keep it, do not strip. Similarly `internal/` is upstream's own Go-side internal libraries (Apache-2.0) — keep.
4. **Never edit upstream Python or Go files casually.** Prefer:
   - Flask blueprint registration / middleware in `api/` (upstream's extension point)
   - LLM-provider plug-in pattern in `rag/llm/` (existing pluggable architecture — `chat_model.py`, `embedding_model.py`, etc.)
   - Bridge webhooks called from `cognis-platform/apps/bridge`
   If you must touch an upstream file, the PR upstream is **mandatory** before merging to `cognis/main`.
5. **Fork-diff cap: 5% of upstream LOC.** Tracked per-PR. Target ≤3%.
6. **Commit prefixes only:** `fork:` / `brand:` / `wire:` / `ci:` / `docs:`.
7. **All Cognis-specific multi-tenant + billing logic goes in Bridge.** This repo holds: Cognis branding overlay (logos in `web/src/`), optional Clerk auth Flask middleware, Cognis LLM-provider plug-in, and FORK.md/CLAUDE.md/CODEOWNERS.
8. **Never `pip install ragflow[<premium-extra>]`.** No such extra exists today. If one appears upstream, CI license-gate must block it before merge.

## Stack (upstream)

- Python 3.12+ (pyproject.toml: `requires-python = ">=3.12,<3.15"`)
- Flask + flask-login + flask-session + quart (HTTP)
- SQLAlchemy via `peewee` ORM (note: NOT plain SQLAlchemy) + Alembic-style migrations? Actually peewee migrations. MySQL primary (`mysql-connector-python`).
- Elasticsearch 8.x (`elasticsearch-dsl==8.12.0`) OR Infinity (`infinity-sdk==0.7.0-dev6`) as vector store (toggled by `DOC_ENGINE` env var)
- MinIO for object storage; valkey (Redis-compatible) for cache
- `uv` package manager + `hatchling` build backend
- Frontend: React + TypeScript + Vite + shadcn/ui + Tailwind + Zustand
- Docker Compose orchestration in `docker/`
- LLM SDKs: see hard rule #2 above
- Document parsing: pypdf, pdfplumber, python-docx, python-pptx, openpyxl, pypandoc, mammoth, tika, calamine, extract-msg, etc.
- OCR + layout: onnxruntime (GPU on x86_64, CPU on darwin/arm64), opencv-python, spacy 3.8, pyclipper
- GraphRAG: graspologic
- Go subsystem in `internal/` and `cmd/` — uses `gorm` (the `License` ORM type lives here; not enterprise-gated, just app-level license tracking)

## Build & test (upstream RAGFlow tooling)

```bash
# Python side
uv sync --python 3.12 --all-extras
uv run python3 download_deps.py
pre-commit install
docker compose -f docker/docker-compose-base.yml up -d  # ES/MySQL/MinIO/Redis
bash docker/launch_backend_service.sh
uv run pytest

# Frontend
cd web && npm install && npm run dev

# Go side
bash run_go_tests.sh
```

Don't run any of this inside the fork until Phase 6 — bootstrap stage is git topology only.

## What lives here

Currently (post-bootstrap):
- `FORK.md`, `CLAUDE.md`, `CODEOWNERS` — fork meta
- `.github/workflows/license-gate.yml` — ScanCode + trap-dir gate
- `.github/workflows/upstream-rebase.yml` — nightly rebase bot (schedule kept commented; flip after first manual rebase)
- `tools/check_no_proprietary.py` — license allowlist enforcement (sits alongside upstream's pre-existing `tools/` subdirs — does not conflict)

Planned (Phase 6):
- `api/cognis/cognis_auth.py` — Clerk JWT validator Flask middleware, calls Bridge for tenant resolution
- `rag/llm/cognis_provider.py` — OpenAI-compatible provider pinned at `llm.cognisai.com`
- `web/src/branding/` — Cognis logos + theme overlay (env-driven)
- Bridge wire-up: tenant_id resolution from `org_mappings`

## Auth pattern with Bridge

Default = Pattern A (Bridge proxy). Cognis portal calls Bridge, Bridge holds RAGFlow admin credentials, Bridge proxies API calls to the RAGFlow server with `Authorization: Bearer <ragflow-admin-key>`. Token never reaches the browser.

Pattern B (Flask middleware in this repo) only if direct RAGFlow UI access is required for "knowledge base inspection" / debug surface for ops. One file: `api/cognis/cognis_auth.py`.

## What NOT to do

- Don't run RAGFlow's hosted-product onboarding scripts (cloud.ragflow.io configs are not for us)
- Don't add NestJS / Bridge logic here — that's in `cognis-platform/apps/bridge`
- Don't touch `vendor/upstream` directly — it's a mirror branch
- Don't commit credentials; `docker/.env` is gitignored upstream
- Don't `pip install litellm[enterprise]` (platform-wide rule from cognis-platform/CLAUDE.md) — Cognis is Apache-2.0 core only
- Don't switch off `uv` / `pre-commit` / `ruff` — keep upstream tooling to minimize rebase friction
- Don't migrate away from peewee or MySQL upstream's choices unless upstream does — every divergence compounds
