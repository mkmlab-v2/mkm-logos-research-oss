"""Tests for eval_btrack_btc_rolling_promotion_gate_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_btrack_btc_rolling_promotion_gate_v1.py"


def test_rolling_gate_runs_on_repo_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out), "--n-folds", "3"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_rolling_promotion_gate_v1"
    assert doc["research_only"] is True
    assert doc["would_change_active"] is False
    assert doc["combined_all_passed"] is False
    assert doc["n_dates_180d"] >= 30
    assert len(doc["policies"]) >= 1
