"""Prefit tune → freeze → prophecy-only honest OOS."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl").is_file(),
    reason="science_core kospi jsonl missing",
)
def test_prefit_panel_pre_may_no_prophecy_overlap():
    cp = subprocess.run(
        [PY, "scripts/build_kospi_field_band_prefit_panel_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    ev = json.loads((ROOT / "reports/kospi_field_band_prefit_panel_eval_v1_latest.json").read_text(encoding="utf-8-sig"))
    dates = {str(r.get("session_date")) for r in ev.get("rows") or []}
    assert all(d < "2026-05-01" for d in dates if d)
    assert int(ev.get("n_scored") or 0) >= 20


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json").is_file(),
    reason="may prophecy missing",
)
def test_prefit_chain_exit_zero():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_prefit_chain_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "reports/kospi_field_band_prefit_frozen_oos_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert doc["protocol"].startswith("prefit_tune")
    pre = doc["prophecy_only_oos"]["prefit_frozen"]
    assert float(pre["delta_stack_minus_base_holdout"] or 0) >= 0.03
    policy = json.loads(
        (ROOT / "docs/final/artifacts/kospi_field_band_conformal_prefit_frozen_policy_v1_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert policy.get("frozen") is True
