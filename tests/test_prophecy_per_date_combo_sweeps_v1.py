# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.5, K:0.2, M:0.2}
# Balance: 92
# Purpose: Smoke tests for per-date combo sweep and holdout scripts
# Keywords: pytest, prophecy, sweep, holdout
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(script: str, out_name: str) -> dict:
    ws = Path(__file__).resolve().parents[1]
    out = ws / "docs" / "final" / "artifacts" / out_name
    proc = subprocess.run(
        [sys.executable, str(ws / "scripts" / script), "--output", str(out)],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def test_per_date_combo_sweep_runs() -> None:
    doc = _run("run_prophecy_per_date_lens_combo_sweep_v1.py", "_tmp_prophecy_per_date_combo_sweep_test.json")
    assert doc.get("schema") == "prophecy_per_date_lens_combo_sweep_v1"
    assert isinstance(doc.get("best_candidate"), dict)


def test_per_date_combo_holdout_runs() -> None:
    doc = _run("run_prophecy_per_date_combo_holdout_v1.py", "_tmp_prophecy_per_date_combo_holdout_test.json")
    assert doc.get("schema") == "prophecy_per_date_combo_holdout_v1"
    assert "test" in doc and "accuracy" in doc["test"]


def test_per_date_combo_walkforward_runs() -> None:
    doc = _run("run_prophecy_per_date_combo_walkforward_v1.py", "_tmp_prophecy_per_date_combo_walkforward_test.json")
    assert doc.get("schema") == "prophecy_per_date_combo_walkforward_v1"
    assert isinstance(doc.get("folds"), list) and len(doc["folds"]) >= 1
    agg = doc.get("aggregate")
    assert isinstance(agg, dict)
    assert "mean_test_accuracy" in agg and "stdev_test_accuracy" in agg
