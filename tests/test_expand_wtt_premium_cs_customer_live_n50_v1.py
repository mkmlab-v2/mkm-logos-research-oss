"""expand_wtt_premium_cs_customer_live_n50_v1 — masking + row transform."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.expand_wtt_premium_cs_customer_live_n50_v1 import (  # noqa: E402
    build_n50_rows,
    mask_pilot_text,
    transform_pilot_row,
)


def test_mask_pilot_text_strips_fill() -> None:
    assert "[FILL:" not in mask_pilot_text("[FILL:환불] 주문 ORD-2026-001 환불")


def test_transform_pilot_row_n50_labels() -> None:
    row = {
        "session_id": "cs-premium-005",
        "domain_tag": "customer-support-chat",
        "labels": ["not_customer_data"],
        "customer_provided": True,
        "turns": [{"role": "user", "text": "ORD-2026-061105"}],
    }
    out = transform_pilot_row(row, target_num=35)
    assert out["session_id"] == "cs-premium-035"
    assert out["customer_provided"] is True
    assert "n50_pilot_masked_derivation_v1" in out["labels"]
    assert "███" in out["turns"][0]["text"]


def test_build_n50_rows_count() -> None:
    pilot = ROOT / "data/wtt/intake/wtt-premium-cs-pilot-v1.jsonl"
    if not pilot.is_file():
        import pytest

        pytest.skip("pilot jsonl missing")
    rows = build_n50_rows(pilot)
    assert len(rows) == 20
    assert rows[0]["session_id"] == "cs-premium-031"
    assert rows[-1]["session_id"] == "cs-premium-050"
