"""Smoke test for BTC decouple spike holdout replay."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_holdout_replay_runs() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_btrack_btc_decouple_spike_holdout_replay_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    out = ROOT / "reports/btrack_btc_decouple_spike_holdout_replay_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_decouple_spike_holdout_replay_v1"
    assert doc["research_only"] is True
    assert len(doc.get("cohorts") or []) >= 2
