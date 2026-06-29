"""calibration30 Phase-2 closure contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_calibration30_closure_happy_path(tmp_path: Path) -> None:
    src = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
    sample = tmp_path / "cal30.json"
    status = tmp_path / "status.json"
    out = tmp_path / "closure.json"
    sample.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    status.write_text(
        json.dumps({"schema": "myeongri_interpret_harness_v3_v4_status_v1", "v4_variant_sft": {}}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_myeongri_interpret_v4_calibration30_closure_v1.py"),
            "--sample-json",
            str(sample),
            "--status-json",
            str(status),
            "--out-json",
            str(out),
            "--skip-radar-update",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(sample.read_text(encoding="utf-8"))
    assert doc["calibration_policy_v1"]["phase"] == "calibration30_closed"
    assert doc["human_verdict_counts"]["pass"] == 30
