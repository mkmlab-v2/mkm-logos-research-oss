"""expand_wtt_premium_cs_customer_live_n30_v1 — masking + row transform."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.expand_wtt_premium_cs_customer_live_n30_v1 import (  # noqa: E402
    build_n30_rows,
    mask_pilot_text,
    transform_pilot_row,
)


def test_mask_pilot_text_ord() -> None:
    assert "███" in mask_pilot_text("환불 보류 건 ORD-2026-061129 사람 연결")


def test_transform_pilot_row_labels() -> None:
    row = {
        "session_id": "cs-premium-029",
        "domain_tag": "customer-support-chat",
        "labels": ["not_customer_data"],
        "customer_provided": True,
        "turns": [{"role": "user", "text": "ORD-2026-061129"}],
    }
    out = transform_pilot_row(row)
    assert out["customer_provided"] is True
    assert "not_customer_data" not in out["labels"]
    assert "n30_pilot_masked_derivation_v1" in out["labels"]
    assert "███" in out["turns"][0]["text"]


def test_build_n30_rows_count() -> None:
    pilot = ROOT / "data/wtt/intake/wtt-premium-cs-pilot-v1.jsonl"
    if not pilot.is_file():
        import pytest

        pytest.skip("pilot jsonl missing")
    rows = build_n30_rows(pilot)
    assert len(rows) == 10
    assert rows[0]["session_id"] == "cs-premium-021"
    assert rows[-1]["session_id"] == "cs-premium-030"
