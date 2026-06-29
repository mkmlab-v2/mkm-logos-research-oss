"""M1 share scrub hypo v1 — mirror of personadiaryShareScrubHypoV1.ts for Fact-Lock pytest."""

from __future__ import annotations

import re

MAX_TEXT = 2000
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?82[-.\s]?)?0?1[0-9][-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)")
PAY_URL_RE = re.compile(r"https?://[^\s]*(?:pay|payment|checkout|mkmlife)[^\s]*", re.I)
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def scrub_share_text_hypo_v1(text: str) -> tuple[str, bool]:
    """Return scrubbed text and whether any redaction was applied."""
    if not isinstance(text, str):
        return "", True
    original = text
    out = text.strip()
    if len(out) > MAX_TEXT:
        out = out[:MAX_TEXT]
    out = EMAIL_RE.sub("[redacted-email]", out)
    out = PAY_URL_RE.sub("[redacted-pay-url]", out)
    out = CARD_RE.sub("[redacted-card]", out)
    out = PHONE_RE.sub("[redacted-phone]", out)
    out = re.sub(r"\s+", " ", out).strip()
    scrubbed = out != original.strip() or len(original.strip()) > MAX_TEXT
    return out, scrubbed
