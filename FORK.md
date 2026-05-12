# Fork of infiniflow/ragflow

This repo is a **soft fork** of [`infiniflow/ragflow`](https://github.com/infiniflow/ragflow), maintained as `cognis-brain-ragflow` under the Cognis AI platform. It is one of three component forks (alongside `cognis-brain-vllm` and `cognis-brain-axolotl`) that make up the Cognis Brain (Phase 6) private-LLM offering. RAGFlow's role: **document ingestion + retrieval — the RAG / context layer that backs Brain-plan tenants.**

## License posture

**Upstream license: plain Apache-2.0.**

Verified verbatim at upstream HEAD SHA `5e46457c28d615aec5f9676740c8408121cdcce7` (2026-05-12):

- Single top-level `LICENSE` file — standard Apache-2.0 preamble through to Appendix, unmodified
- **NO Commons Clause rider, NO Sustainable Use rider, NO Elastic License addendum**
- No `LICENSE.commercial` / `LICENSE.enterprise` / `COPYING.addendum` / `NOTICE` files anywhere
- `pyproject.toml` declares `license-files = ["LICENSE"]` — the single LICENSE governs the entire codebase
- Upstream README license badge: `License-Apache--2.0`
- No `enterprise/`, `ee/`, `cloud/`, `pro/`, `saas/`, `premium/`, or `platform/` directories at any depth
- Per-file copyright headers across both Python (`api/`, `admin/`) and Go (`internal/`, `cmd/`) trees carry the plain Apache-2.0 boilerplate

The doctrine prior to this fork's bootstrap flagged a concern about a possible "Apache-2.0 + Commons Clause" rider on RAGFlow. **That concern was investigated and is not present at this SHA.** ScanCode-style license-bleed remains enforced via CI (`tools/check_no_proprietary.py` blocks `commons-clause` prefix among others) so any future upstream relicense would be caught.

**One trap-shaped artifact to be aware of (NOT a license trap):** upstream ships an Apache-2.0-licensed Go `License` ORM entity at `internal/entity/license.go` + `internal/dao/license.go` storing an encrypted-payload `license` DB record. This is application-level (a Sentry-style license-key acceptance store for the self-hosted admin pane), NOT a code-license restriction — the surrounding code is openly Apache-2.0 redistributable. No action required; flagged here so future rebase-resolvers know this isn't a paywall.

`cognis-brain-ragflow` is the document-ingestion + retrieval product (Phase 6, component) of the Cognis platform. See [`cognis-platform`](https://github.com/cognis-ai/cognis-platform) for the shared brain (Bridge, LiteLLM proxy, Clerk auth, billing).

## Branches

| Branch | Purpose |
|---|---|
| `vendor/upstream` | Mirror of `infiniflow/ragflow:main`. NEVER edit. Rebased by the nightly bot. |
| `cognis/main` | Cognis work. Rebased monthly onto `vendor/upstream`. Default branch. |

## Commit prefixes (grep-friendly across rebases)

- `fork:` — surgical edits to upstream files (last resort; prefer Bridge integration)
- `brand:` — branding (logos, theme, copy)
- `wire:` — Cognis integration plumbing (Clerk-via-Bridge auth, LLM-client wrap, Bridge API calls)
- `ci:` — GitHub Actions, license gate, rebase bot
- `docs:` — FORK.md, CLAUDE.md, CODEOWNERS, READMEs

## Bootstrap state

This fork's `cognis/main` is `vendor/upstream` + a single `chore: cognis-brain-ragflow fork bootstrap` commit dropping in fork templates. No upstream files have been modified. No directories stripped — upstream is single-license Apache-2.0 with no trap directories.

If a future upstream change introduces a proprietary directory (`/enterprise/`, `/ee/`, `/cloud/`, `/pro/`, `/saas/`, `/platform/`), the license-gate CI will fail; resolve by stripping in a dedicated `chore: strip <dir>` commit on `cognis/main` and adding the path to the rebase bot's modify-delete auto-resolver.

## Fork-diff target

≤3% of upstream LOC (default per fork-ops.md). RAGFlow is a large codebase (~3000 files) so the headroom is substantial in LOC terms — but the discipline is still to push customization into Bridge, not the fork. Tracked on every PR via `git diff vendor/upstream...cognis/main --stat`. Hard cap 5% — build fails above that.

## Rebase cadence

- Nightly bot: `.github/workflows/upstream-rebase.yml` exists but `cron` is intentionally commented out for bootstrap (Phase 6 not active). Flip after Phase 6 work starts.
- Auto-merge clean rebases via Mergify (configured at platform level once first rebase lands)
- Conflicts → bot opens issue labeled `rebase-conflict`; human review
- Shared `rerere-cache` committed to `cognis-platform/infra/rerere-cache/cognis-brain-ragflow/`

## Cognis-side surface (Phase 6)

What lives on `cognis/main` (and ONLY here):

- `FORK.md`, `CLAUDE.md`, `CODEOWNERS` — fork meta
- `.github/workflows/license-gate.yml` — ScanCode allowlist enforcement
- `.github/workflows/upstream-rebase.yml` — nightly rebase bot (currently dormant)
- `tools/check_no_proprietary.py` — license allowlist enforcement script
- (future) `api/cognis/cognis_auth.py` — Clerk JWT validator, calls Bridge for `org_id` → RAGFlow `tenant_id` resolution
- (future) `rag/llm/cognis_provider.py` — OpenAI-compatible provider pinned at `llm.cognisai.com` (the LiteLLM proxy); replaces direct OpenAI / Anthropic / Cohere calls
- (future) `web/src/branding/` — Cognis logos + theme overlay
- (future) Bridge-mediated multi-tenancy: RAGFlow's native `tenant_id` resolves from Bridge's `org_mappings` table

All product-level multi-tenant + billing logic lives in `cognis-platform/apps/bridge`, NOT here.

## Upstream-PR policy

Contribute back to `infiniflow/ragflow` *before* merging to `cognis/main`:

- Bug fixes, perf patches, test improvements, type fixes, i18n, refactors that shrink fork diff

Keep in fork (do NOT upstream):

- Clerk / Stripe / LiteLLM-gateway / Cognis-branded code
- Cognis-specific multi-tenant primitives, billing meters, audit integration with Bridge
- Replacement of RAGFlow's direct provider SDK calls (`anthropic`, `cohere`, `openai`-via-`litellm`, `dashscope`, `groq`, etc. — see `pyproject.toml`) with the Cognis LLM client / `llm.cognisai.com` proxy

## References

- Fork-ops doctrine: `cognis-platform/docs/specs/fork-ops.md`
- LLM proxy contract: `cognis-platform/docs/specs/ai-gateway.md`
- Bridge service: `cognis-platform/docs/specs/bridge-service.md`
- Sibling Brain forks: `cognis-ai/cognis-brain-vllm`, `cognis-ai/cognis-brain-axolotl`
