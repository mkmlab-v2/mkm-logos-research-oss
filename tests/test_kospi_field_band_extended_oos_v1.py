"""L2 extended OOS — multi-month panel + band WF gates."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_multi_month_panel_merges_without_overlap():
    from scripts.build_kospi_multi_month_prophecy_panel_v1 import build_multi_month_panel
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    may_ev = _read(ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json")
    jun_ev = _read(ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json")
    may_cal = _read(ROOT / "reports/kospi_202605_daily_prophecy_calendar_research.json")
    jun_cal = _read(ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json")
    if not all((may_ev, jun_ev, may_cal, jun_cal)):
        pytest.skip("may/june artifacts missing")

    ev, cal = build_multi_month_panel(
        eval_paths=[
            ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json",
            ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        ],
        calendar_paths=[
            ROOT / "reports/kospi_202605_daily_prophecy_calendar_research.json",
            ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json",
        ],
        include_science_backfill=False,
    )
    assert ev["n_scored"] == 34
    assert ev["n_months"] == 2
    assert cal["n_trading_days"] >= 34


def test_science_backfill_adds_rows():
    from scripts.build_kospi_multi_month_prophecy_panel_v1 import build_multi_month_panel

    if not (ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl").is_file():
        pytest.skip("science jsonl missing")

    ev, _cal = build_multi_month_panel(
        eval_paths=[
            ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json",
            ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        ],
        calendar_paths=[
            ROOT / "reports/kospi_202605_daily_prophecy_calendar_research.json",
            ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json",
        ],
        include_science_backfill=True,
        science_date_from="2026-01-02",
        science_date_to="2026-04-30",
    )
    assert ev["n_scored"] >= 70
    assert ev.get("science_backfill_rows", 0) > 0
    assert ev["n_months"] >= 4


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json").is_file(),
    reason="eval artifacts missing",
)
def test_extended_oos_chain_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_extended_oos_v1.py", "--skip-may-eval"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads((ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert doc["ladder_stage"] == "L2_extended_oos"
    gates = doc["l2_gates"]
    assert gates["holdout_n"] >= 30
    assert gates["checks"]["multi_month_ge_2"] is True
    assert gates["checks"]["shadow_parity"] is True
