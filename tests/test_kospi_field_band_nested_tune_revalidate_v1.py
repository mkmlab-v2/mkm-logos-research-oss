"""Nested tune revalidate on June prophecy holdout."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json").is_file(),
    reason="panel missing",
)
def test_nested_revalidate_runs():
    cp = subprocess.run(
        [PY, "scripts/run_kospi_field_band_nested_tune_revalidate_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (ROOT / "reports/kospi_field_band_nested_tune_revalidate_v1_latest.json").read_text(encoding="utf-8-sig")
    )
    assert doc["june_holdout_prophecy_n"] >= 10
    assert "june_holdout_metrics" in doc
