"""Match rate delta report smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DELTA = ROOT / "reports/tkm_match_rate_delta_report_v1_latest.json"


def test_delta_report() -> None:
    if not DELTA.is_file():
        pytest.skip("delta report missing")
    doc = json.loads(DELTA.read_text(encoding="utf-8-sig"))
    assert doc.get("delta_kpi_ok") is True
    assert doc.get("match_rate_delta_encounter_minus_clinic") is not None
    breakdown = doc.get("encounter_breakdown")
    assert isinstance(breakdown, dict)
    assert int(breakdown.get("multiturn_count") or 0) >= 1
