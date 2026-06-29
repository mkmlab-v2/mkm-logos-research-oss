"""Prophecy-only panel OOS chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_prophecy_only_inputs_include_jan_apr_slots():
    from scripts.kospi_prophecy_only_panel_inputs_v1 import PROPHECY_MONTH_SOURCES

    tags = [t for t, _, _ in PROPHECY_MONTH_SOURCES]
    assert tags[:4] == ["202601", "202602", "202603", "202604"]


def test_prophecy_only_panel_no_backfill():
    from scripts.build_kospi_prophecy_only_panel_v1 import main as build_main

    # import via subprocess for exit code
    cp = subprocess.run(
        [PY, "scripts/build_kospi_prophecy_only_panel_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    ev = json.loads((ROOT / "reports/kospi_prophecy_only_panel_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    assert ev.get("science_backfill_rows", 0) == 0
    assert int(ev.get("n_scored") or 0) >= 100


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json").is_file(),
    reason="may eval missing",
)
def test_prophecy_only_chain_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_prophecy_only_chain_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    oos = json.loads(
        (ROOT / "reports/kospi_field_band_prophecy_only_oos_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert oos["gates"]["science_backfill_rows_zero"] is True
    hold_n = int((oos["holdout_pooled"]["stack_union"] or {}).get("n_scored") or 0)
    assert hold_n >= 30
    assert oos.get("primary_may_june_holdout")
    guard = oos["small_sample_guardrails"]
    if hold_n >= int(guard.get("holdout_n_discussion_min") or 30) and int(
        guard.get("total_scored_n") or 0
    ) >= int(guard.get("total_scored_headline_min") or 40):
        assert guard["track_a_discussion_eligible"] is True
        assert guard.get("blockers") in (None, [])
    else:
        assert guard["track_a_discussion_eligible"] is False
