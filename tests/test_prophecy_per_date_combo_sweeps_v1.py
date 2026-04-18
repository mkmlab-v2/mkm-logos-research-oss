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


def test_walkforward_clamps_n_folds_to_distinct_dates(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[1]
    rows: list[dict] = []
    for day in (10, 11, 12, 13, 14, 15):
        ed = f"2026-01-{day:02d}"
        rows.append(
            {"instrument": "kospi", "eval_date": ed, "predicted_direction": "bull", "actual_direction": "bull"},
        )
        rows.append({"instrument": "btc", "eval_date": ed, "predicted_direction": "bull", "actual_direction": "bull"})
    score_path = tmp_path / "wf_score.json"
    score_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    out = tmp_path / "wf_out.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "run_prophecy_per_date_combo_walkforward_v1.py"),
            "--score-json",
            str(score_path),
            "--n-folds",
            "100",
            "--output",
            str(out),
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    inp = doc.get("inputs") or {}
    assert inp.get("n_folds_requested") == 100
    assert inp.get("n_folds_effective") == 6
    assert inp.get("n_folds_clamped") is True
