"""Weekly encounter_sequence report multiturn churn KPI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_weekly_multiturn_churn_kpi() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    churn = doc.get("multiturn_churn_kpi")
    assert isinstance(churn, dict)
    assert churn.get("multiturn_churn_ok") is True
    assert (churn.get("avg_turn_count") or 0) >= 1.0
    headline = doc.get("headline_kpi")
    assert isinstance(headline, dict)
    assert headline.get("dual_lane_headline_ok") is True
    assert headline.get("encounter_match_rate") is not None
    delta = doc.get("match_rate_delta_kpi")
    assert isinstance(delta, dict)
    assert delta.get("delta_kpi_ok") is True
    l5 = doc.get("l5_myeongni_kpi")
    assert isinstance(l5, dict)
    assert l5.get("l5_myeongni_headline_ok") is True
