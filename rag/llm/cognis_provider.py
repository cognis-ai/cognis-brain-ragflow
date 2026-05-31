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

Wire-up (one upstream-touch line in rag/llm/__init__.py):
    from rag.llm.cognis_provider import register_cognis_provider
    register_cognis_provider()

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
    try:
        from rag.llm import ChatModel, EmbeddingModel  # type: ignore[attr-defined]
    except ImportError:
        # Upstream layout changed — log + bail. Operator can wire manually.
        return

    # RAGFlow's ChatModel / EmbeddingModel dicts map factory name → class.
    # OpenAI-compat shape is already supported via the OpenAI factory class
    # taking an arbitrary base_url; we alias "Cognis" to the same class so
    # the admin UI dropdown shows our brand instead of "OpenAI".
    try:
        openai_chat_cls = ChatModel.get("OpenAI")
        openai_embed_cls = EmbeddingModel.get("OpenAI")
    except Exception:
        return

    if openai_chat_cls and "Cognis" not in ChatModel:
        ChatModel["Cognis"] = openai_chat_cls
    if openai_embed_cls and "Cognis" not in EmbeddingModel:
        EmbeddingModel["Cognis"] = openai_embed_cls


def default_tenant_llm_config() -> Mapping[str, Any]:
    """Snippet a portal CTA can copy/paste into a RAGFlow Tenant config."""
    return {
        "llm_factory": "Cognis",
        "api_base": gateway_url(),
        "chat_model_name": DEFAULT_SMART_MODEL,
        "fast_model_name": DEFAULT_FAST_MODEL,
        "embedding_model_name": DEFAULT_EMBED_MODEL,
    }
