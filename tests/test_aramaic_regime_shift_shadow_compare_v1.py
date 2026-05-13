"""Smoke: run_aramaic_regime_shift_shadow_compare_v1 reads score JSON and writes compare + best score."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_aramaic_regime_shift_shadow_compare_v1.py"


def test_aramaic_regime_shift_shadow_compare_cli_smoke(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    cmp_out = tmp_path / "compare.json"
    best_out = tmp_path / "best.json"
    score.write_text(
        json.dumps(
            {
                "schema": "aramaic_regime_shift_score_v1",
                "shift_score": 0.55,
                "insight_delta_applied": 0.01,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--score-json",
            str(score),
            "--output-json",
            str(cmp_out),
            "--best-output-json",
            str(best_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    cmp_doc = json.loads(cmp_out.read_text(encoding="utf-8"))
    assert cmp_doc.get("schema") == "aramaic_regime_shift_shadow_compare_v1"
    best_doc = json.loads(best_out.read_text(encoding="utf-8"))
    assert best_doc.get("schema") == "aramaic_regime_shift_score_v1"
