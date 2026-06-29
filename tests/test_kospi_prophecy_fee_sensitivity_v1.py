"""KOSPI neutral-band fee sensitivity [HYPO]."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_kospi_prophecy_neutral_band_fee_sensitivity_v1 import build_fee_sensitivity_report

ROOT = Path(__file__).resolve().parents[1]


def test_fee_sensitivity_widening_bps_reduces_directional_bets():
    calendar = {
        "year_month": "2026-06",
        "trading_days": ["2026-06-02", "2026-06-03"],
        "rows": [
            {"session_date": "2026-06-02", "predicted_direction": "bull"},
            {"session_date": "2026-06-03", "predicted_direction": "bear"},
        ],
    }
    cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    if not cal_path.is_file():
        return
    real_cal = json.loads(cal_path.read_text(encoding="utf-8-sig"))
    doc = build_fee_sensitivity_report(
        real_cal,
        calendar_path=cal_path,
        as_of_kst=str(real_cal.get("seal_date") or "2026-06-26")[:10],
        bps_grid=(5.0, 25.0),
        year_month="2026-06",
    )
    assert doc["schema"] == "kospi_prophecy_neutral_band_fee_sensitivity_v1"
    sweep = doc["sweep"]
    assert len(sweep) == 2
    narrow = sweep[0]["metrics"]["n_directional_bets"]
    wide = sweep[1]["metrics"]["n_directional_bets"]
    assert wide <= narrow


def test_july_readiness_pre_month():
    from scripts.build_kospi_july_forward_oos_readiness_v1 import build_july_readiness

    cal = {
        "trading_days": ["2026-07-01", "2026-07-02"],
        "year_month": "2026-07",
    }
    doc = build_july_readiness(calendar=cal, eval_doc={"rows": []}, as_of_kst="2026-06-26")
    assert doc["status"] == "pre_month_calendar_only"
    assert doc["n_scored"] == 0
