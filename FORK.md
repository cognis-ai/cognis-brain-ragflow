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

This fork's `cognis/main` is `vendor/upstream` + a single `chore: cognis-brain-ragflow fork bootstrap` commit dropping in fork templates. No directories stripped — upstream is single-license Apache-2.0 with no trap directories. Upstream-file edits made since bootstrap are logged in the ledger below.

## Upstream-file edit ledger (`fork:` commits — keep current)

Every entry must stay minimal, carry its justification, and be re-verified at each rebase. Per fork-ops, Cognis-specific changes are NOT upstreamed; these are all Cognis-specific wiring with no generic value to infiniflow/ragflow.

| File | Edit | Why (and why no additive mechanism exists) |
|---|---|---|
| `api/ragflow_server.py` | +3 lines: import + `register_cognis_auth(app)` mount | Gate-1 defect 5 / AR-13: the Clerk hook must be installed on the in-process Quart app before serving. Gate 2 struck boot-time seds of server Python as forbidden, and a subprocess `python -c` cannot mutate the server process — the app-init module is the only sanctioned mount point (sso-engineering-spec §4.6 directs exactly this line). Env-gated: no-op unless `JWT_PUBLIC_KEY_URL` is set. |
| `rag/llm/__init__.py` | +5 lines at EOF: import + `register_cognis_provider()` | Gate-1 defect 4 / AR-1a: the `ChatModel`/`EmbeddingModel` dicts are per-process; registration must run inside every server/executor that imports `rag.llm`. This is the wire-up the provider's own docstring specifies; the previous `Dockerfile.cognis` subprocess registration was discarded at exec. Idempotent; rebase conflict surface is the file tail only. |
| `conf/llm_factories.json` | +1 factory block: `"Cognis"` (cognis-smart / cognis-fast / cognis-embed) | Gate-1 defect 4 / AR-1b: `init_llm_factory()` wipes and reseeds `LLMFactories`/`LLM` from this file at every boot, so a provision-time seed would be deleted on restart — the catalog entry is the upstream-sanctioned seeding path. Without it `POST /v1/llm/set_api_key` (`llm_factory: "Cognis"`) and the `Cognis@cognis-smart` tenant defaults have no rows to bind. Additive JSON; rebases merge clean unless upstream reorders the array head. |
| `CLAUDE.md` | fork-template replacement (bootstrap) | Docs-only fork governance; recorded at Gate 2 (take-ours on rebase). |

### In-image boot-time overlays (NOT repo edits — zero git fork-diff, but rebase-sensitive)

These mutate upstream-owned files **inside the running image only** (theming spec + Gate 2 verification 2026-06-10). They are anchor-based and fail open: re-verify each at every rebase, with the Playwright branding suite (`cognis/e2e`) as the acceptance gate.

| In-image target | Mechanism | Guard |
|---|---|---|
| `/ragflow/web/dist` (`*.js/.html/.svg/.json`) | entrypoint sed: `RAGFlow` → `${COGNIS_PRODUCT_NAME}` (case-sensitive), plus B2 URL re-points (`github.com/infiniflow/ragflow`, `ragflow.io/docs...`, `cloud.ragflow.io...` → `COGNIS_PORTAL_URL`/`COGNIS_DOCS_URL`) | e2e G1–G3 (name) + G5 (hrefs) |
| `/ragflow/api/utils/web_utils.py` | entrypoint sed of the single literal `"RAGFlow Invitation"` → `"${COGNIS_PRODUCT_NAME} Invitation"`. **Gate 2 hard ceiling:** the only sanctioned server-side Python sed, ever; widening it or sed'ing `api/apps/__init__.py` (B4 fallback) is STRUCK — re-review required | e2e G7 (MailHog subject) |
| `/ragflow/conf/service_conf.yaml.template` | replaced at build by `cognis-brand-assets/service_conf.cognis.yaml.template` (smtp block env-driven, inert by default) | `tools/check_conf_template_drift.py` in CI (`brand-guard.yml`, `publish-ghcr.yml`) |

All three are gated on `COGNIS_BRANDING=on` (except the template COPY, which is inert without `SMTP_*` env) and preceded by the B6 charset/URL validation of `COGNIS_PRODUCT_NAME`/`COGNIS_DOCS_URL`/`COGNIS_PORTAL_URL` in the entrypoint shim — unsafe values fail the boot instead of corrupting the sed programs.

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
- `api/cognis/cognis_auth.py` — Clerk JWT validator (Quart `before_request` hook), calls Bridge for `org_id` → RAGFlow `tenant_id` resolution; deny-by-default with a public-route allowlist (SEC-5); mounted from `api/ragflow_server.py` (see ledger)
- `rag/llm/cognis_provider.py` — "Cognis" factory pinned at `llm.cognisai.com` (the LiteLLM proxy), aliasing upstream's OpenAI-compatible adapters; registered from `rag/llm/__init__.py` (see ledger) and catalogued in `conf/llm_factories.json`
- `Dockerfile.cognis` — Cognis Knowledge image: brand env + entrypoint shim (B6-validated, digest-pinned base), `REGISTER_ENABLED=0` default (SEC-5), bakes the fork sources over the upstream base image paths
- `cognis-brand-assets/` — brand asset staging: `service_conf.cognis.yaml.template` (B3.1 in-image conf shadow); the Cognis Knowledge logo SVG + theme CSS land here when design delivers (B1/B5)
- `tools/check_conf_template_drift.py` — scripted B3.1 drift gate (Gate 2 condition)
- `.github/workflows/brand-guard.yml` — runs the drift gate on brand-layer PRs/pushes
- `.github/workflows/publish-ghcr.yml` — builds `Dockerfile.cognis` → `ghcr.io/cognis-ai/knowledge` on version tags + dispatch (deployment map §4.1; Coolify consumes digests)
- `cognis/e2e/` — Playwright suite against the live :9382 instance (auth posture, branding incl. G5 href gate + G7 invite-mail subject, core flow)
- `test/unit_test/api/cognis/` — unit tests for the Clerk hook's deny-by-default contract
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
