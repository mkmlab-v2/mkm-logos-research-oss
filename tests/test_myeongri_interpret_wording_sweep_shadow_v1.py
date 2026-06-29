# Purpose: wording sweep shadow replay smoke.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wording_sweep_shadow_runs() -> None:
    out = ROOT / "reports/myeongri_interpret_v4_wording_sweep_shadow_latest.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_myeongri_interpret_v4_wording_sweep_shadow_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["rows_replayed"] == 30
    assert doc["track_wall"]["preds_mutated"] is False
