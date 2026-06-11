"""Cognis Knowledge — LiteLLM provider for RAGFlow.

Registers a "Cognis" LLM factory entry so RAGFlow's `TenantLLM` rows can
point at `llm.cognisai.com` (the Cognis LiteLLM proxy) instead of OpenAI /
Anthropic / etc. directly. This is the productization swap point per
cognis-brain-ragflow/CLAUDE.md hard rule #2 and cost-policy.md section 2.

Usage (operator-side, RAGFlow admin UI):
    Tenant LLM → factory="Cognis" → api_key=<litellm-virtual-key>
                                    → api_base=https://llm.cognisai.com/v1
                                    → model_name=cognis-smart

The factory simply re-uses RAGFlow's built-in OpenAI-compatible chat /
embedding adapters (they already accept `base_url`). No new code path — we
just provide a stable factory name + a sensible default api_base.

Wire-up (Gate-1 defect 4): `rag/llm/__init__.py` calls
`register_cognis_provider()` at the end of its registry build (the single
fork-touch on that upstream file), so the factory exists in every process
that loads the model registries — API server and task executors alike.
The matching `LLMFactories`/`LLM` rows are seeded from the "Cognis" entry
in `conf/llm_factories.json`.

Or set the env var COGNIS_LLM_GATEWAY=https://llm.cognisai.com/v1 and the
factory picks it up at registration time.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

DEFAULT_GATEWAY_URL = "https://llm.cognisai.com/v1"
DEFAULT_SMART_MODEL = "cognis-smart"
DEFAULT_FAST_MODEL = "cognis-fast"
DEFAULT_EMBED_MODEL = "cognis-embed"


def gateway_url() -> str:
    return os.environ.get("COGNIS_LLM_GATEWAY", DEFAULT_GATEWAY_URL)


def register_cognis_provider() -> None:
    """Idempotent factory registration. Safe to call multiple times."""
    import sys

    # Called from the tail of rag/llm/__init__.py, where the module is
    # mid-execution — pull it from sys.modules instead of re-importing.
    llm_registry = sys.modules.get("rag.llm")
    if llm_registry is None:
        try:
            import rag.llm as llm_registry  # type: ignore[no-redef]
        except ImportError:
            # Upstream layout changed — bail. Operator can wire manually.
            return

    chat_models = getattr(llm_registry, "ChatModel", None)
    embed_models = getattr(llm_registry, "EmbeddingModel", None)
    if not isinstance(chat_models, dict) or not isinstance(embed_models, dict):
        return

    # RAGFlow's ChatModel / EmbeddingModel dicts map factory name → class.
    # Alias "Cognis" to the plain OpenAI-SDK adapters that honour an
    # arbitrary base_url. NOT the "OpenAI" chat entry: that resolves to
    # LiteLLMBase, which only forwards api_base for provider names it
    # knows (FACTORY_DEFAULT_BASE_URL) — "Cognis" would silently lose the
    # gateway URL and route nowhere.
    chat_cls = chat_models.get("OpenAI-API-Compatible")
    embed_cls = embed_models.get("OpenAI") or embed_models.get("OpenAI-API-Compatible")

    if chat_cls and "Cognis" not in chat_models:
        chat_models["Cognis"] = chat_cls
    if embed_cls and "Cognis" not in embed_models:
        embed_models["Cognis"] = embed_cls


def default_tenant_llm_config() -> Mapping[str, Any]:
    """Snippet a portal CTA can copy/paste into a RAGFlow Tenant config."""
    return {
        "llm_factory": "Cognis",
        "api_base": gateway_url(),
        "chat_model_name": DEFAULT_SMART_MODEL,
        "fast_model_name": DEFAULT_FAST_MODEL,
        "embedding_model_name": DEFAULT_EMBED_MODEL,
    }
