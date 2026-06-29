"""Share scrub hypo v1 — mirrors personadiaryShareScrubHypoV1.ts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from personadiary_share_scrub_hypo_v1 import scrub_share_text_hypo_v1  # noqa: E402


def test_scrub_redacts_email() -> None:
    text, scrubbed = scrub_share_text_hypo_v1("hello commander@example.com ok")
    assert "[redacted-email]" in text
    assert scrubbed is True


def test_scrub_redacts_mkmlife_pay_url() -> None:
    text, scrubbed = scrub_share_text_hypo_v1("see https://mkmlife.com/pay/checkout now")
    assert "[redacted-pay-url]" in text
    assert scrubbed is True


def test_scrub_plain_text_unchanged() -> None:
    text, scrubbed = scrub_share_text_hypo_v1("오늘 산책했다")
    assert text == "오늘 산책했다"
    assert scrubbed is False
