"""Smoke test for continuous calibration holdout replay."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_continuous_calibration_holdout_replay_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_btrack_btc_continuous_calibration_holdout_replay_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    doc = json.loads((ROOT / "reports/btrack_btc_continuous_calibration_holdout_replay_v1_latest.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_continuous_calibration_holdout_replay_v1"
    assert len(doc.get("cohorts") or []) >= 2
