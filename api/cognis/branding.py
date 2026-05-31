"""Cognis Knowledge — RAGFlow brand identity constants."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CognisBrand:
    product_name: str = "Cognis Knowledge"
    product_tagline: str = "Answers questions from your documents."
    product_job: str = (
        "Index your knowledge base, answer questions across it with citations, "
        "and feed the answers into every Cognis product that asks."
    )
    support_email: str = "support@cognisai.com"
    docs_url: str = "https://cognisai.com/docs/knowledge"
    portal_url: str = "https://app.cognisai.com/dashboard/knowledge"


def load_brand() -> CognisBrand:
    return CognisBrand(
        product_name=os.environ.get("COGNIS_PRODUCT_NAME", CognisBrand.product_name),
        product_tagline=os.environ.get("COGNIS_PRODUCT_TAGLINE", CognisBrand.product_tagline),
        product_job=os.environ.get("COGNIS_PRODUCT_JOB", CognisBrand.product_job),
        support_email=os.environ.get("COGNIS_SUPPORT_EMAIL", CognisBrand.support_email),
        docs_url=os.environ.get("COGNIS_DOCS_URL", CognisBrand.docs_url),
        portal_url=os.environ.get("COGNIS_PORTAL_URL", CognisBrand.portal_url),
    )


def branding_enabled() -> bool:
    return os.environ.get("COGNIS_BRANDING", "").strip().lower() in ("on", "true", "1", "yes")
