# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_lens_opt_in_confidence_sweep_single_point(tmp_path: Path) -> None:
    v1 = ROOT / "reports/btrack_prophecy_score_ensemble_v2_baseline_v1_latest.json"
    v2 = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
    if not v1.is_file() or not v2.is_file():
        pytest.skip("baseline artifacts missing")
    out = tmp_path / "sweep.json"
    sweep_dir = tmp_path / "sweep"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1.py"),
            "--confidence-grid",
            "0.18",
            "--sweep-dir",
            str(sweep_dir),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_ensemble_v2_lens_opt_in_confidence_sweep_v1"
    assert len(doc["rows"]) == 1
    assert doc["rows"][0]["lens_mean_test_accuracy"] is not None
