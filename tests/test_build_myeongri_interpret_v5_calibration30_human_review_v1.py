"""v5 calibration30 sample builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_v5_calibration30_sample_smoke() -> None:
    out = ROOT / "reports/myeongri_interpret_v5_human_review_calibration30_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_myeongri_interpret_v5_calibration30_human_review_v1.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongri_interpret_v5_human_review_calibration30_v1"
    assert len(doc["samples"]) == 30
    assert doc["samples"][0].get("v4_phase2_verdict") is not None
