"""calibration30 commander apply contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_calibration30_apply_all_rows(tmp_path: Path) -> None:
    src = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
    sample = tmp_path / "cal30.json"
    sample.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_myeongri_interpret_v4_calibration30_commander_review_v1.py"),
            "--sample-json",
            str(sample),
            "--status-json",
            str(tmp_path / "missing_status.json"),
            "--skip-radar-update",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(sample.read_text(encoding="utf-8"))
    assert doc["human_verdict_counts"]["pass"] + doc["human_verdict_counts"]["needs_edit"] == 30
    assert doc["human_verdict_counts"]["fail"] == 0
    assert all(s.get("reviewer_verdict") for s in doc["samples"])
