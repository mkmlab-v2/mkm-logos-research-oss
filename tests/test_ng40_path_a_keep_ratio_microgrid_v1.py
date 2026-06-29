"""Smoke for Path A keep_ratio microgrid."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/ng40_path_a_keep_ratio_microgrid_v1_latest.json"
GOLDEN = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"


def test_path_a_keep_ratio_microgrid_exit_0() -> None:
    if not GOLDEN.is_file():
        return
    proc = subprocess.run(
        [
            PY,
            "scripts/run_ng40_path_a_keep_ratio_microgrid_v1.py",
            "--keep-ratios",
            "0.82",
            "0.88",
            "--output",
            "reports/_test_path_a_keep_ratio_microgrid_v1.json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "reports/_test_path_a_keep_ratio_microgrid_v1.json").read_text(encoding="utf-8")
    )
    assert doc["schema"] == "ng40_path_a_keep_ratio_microgrid_v1"
    assert len(doc["golden40"]["sweep"]) == 2
    assert doc["golden40"]["sweep"][0]["byte_exact_subset_parity"] == 1.0
