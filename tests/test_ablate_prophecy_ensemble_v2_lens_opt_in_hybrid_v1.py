# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_ensemble_v2_lens_opt_in_hybrid_patch_smoke(tmp_path: Path) -> None:
    v1 = ROOT / "reports/btrack_prophecy_score_ensemble_v2_baseline_v1_latest.json"
    v2 = ROOT / "reports/btrack_ensemble_per_date_directions_v2_latest.json"
    if not v1.is_file() or not v2.is_file():
        pytest.skip("baseline score or v2 directions missing")
    out = tmp_path / "hybrid_ablation.json"
    score_out = tmp_path / "hybrid_score.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ablate_prophecy_ensemble_v2_lens_opt_in_hybrid_v1.py"),
            "--skip-hybrid-run",
            "--hybrid-score-out",
            str(score_out),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "prophecy_ensemble_v2_lens_opt_in_hybrid_ablation_v1"
    score = json.loads(score_out.read_text(encoding="utf-8"))
    patched = [r for r in score["rows"] if "ensemble_v2_lens_opt_in_direction" in r]
    assert len(patched) >= 1
