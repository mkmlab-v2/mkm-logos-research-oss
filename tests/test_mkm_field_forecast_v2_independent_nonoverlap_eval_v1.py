#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin tests for Field Forecast V2 independent non-overlap eval."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "docs/final/artifacts/mkm_field_stock_forecast_v2_phase2_walkforward_latest.json"
PHASE3 = ROOT / "docs/final/artifacts/mkm_field_stock_forecast_v2_phase3_qualification_latest.json"
ALLOWED = {"PASS", "ZERO_CANDIDATE", "INSUFFICIENT_DATA"}


def _run(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_independent_nonoverlap_eval_runner_exit0() -> None:
    before2 = PHASE2.read_bytes() if PHASE2.is_file() else None
    before3 = PHASE3.read_bytes() if PHASE3.is_file() else None
    r = _run("run_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py")
    assert r.returncode == 0, r.stdout + r.stderr
    summary_path = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_v1_latest.json"
    assert summary_path.is_file()
    doc = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    assert doc.get("pass_ceiling") == "INDEPENDENT_NONOVERLAP_QUALIFICATION_ONLY"
    assert doc.get("observed_result") in ALLOWED
    assert doc.get("SIGNAL_CANDIDATE_claimed") is False
    assert doc.get("MARKET_ALPHA_ESTABLISHED") is False
    assert doc.get("includes_3_lens") is False
    assert doc.get("tuning_after_results") is False
    assert doc.get("AUTO_NEXT") is False
    assert doc.get("on_pass") == "STOP"
    assert doc.get("ORACLE_SESSION_UPGRADE") == "FAIL"
    wm = doc.get("window_meta") or {}
    assert wm.get("selection_rule") == "reserved_future_unseen_only_no_historical_backfill"
    assert str(wm.get("reserved_future_date_start") or "") == "2026-09-03"
    assert doc.get("label") == "independent_nonoverlap_reserved_future"
    ds = wm.get("date_start")
    if ds:
        assert str(ds) >= "2026-09-03"
    if doc.get("zero_frozen_wf_folds") or int(doc.get("n_pred_rows") or 0) == 0:
        assert doc.get("observed_result") == "INSUFFICIENT_DATA"
    receipt = json.loads(
        (
            ROOT
            / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_observed_result_receipt_v1.json"
        ).read_text(encoding="utf-8-sig")
    )
    assert receipt.get("observed_result") == doc.get("observed_result")
    assert receipt.get("ORACLE_SESSION_UPGRADE") == "FAIL"
    if before2 is not None:
        assert PHASE2.read_bytes() == before2
    if before3 is not None:
        assert PHASE3.read_bytes() == before3


def test_independent_nonoverlap_eval_checker_exit0() -> None:
    r0 = _run("run_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py")
    assert r0.returncode == 0, r0.stdout + r0.stderr
    r = _run("check_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py")
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads(
        (
            ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_check_v1_latest.json"
        ).read_text(encoding="utf-8-sig")
    )
    assert report.get("ok") is True
    assert report.get("observed_result") in ALLOWED
    assert report.get("ORACLE_SESSION_UPGRADE") == "FAIL"
    assert report.get("AUTO_NEXT") is False
    assert report.get("on_pass") == "STOP"
