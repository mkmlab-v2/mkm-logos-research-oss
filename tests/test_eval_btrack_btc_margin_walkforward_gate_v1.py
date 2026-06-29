"""Tests for eval_btrack_btc_margin_walkforward_gate_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_btrack_btc_margin_walkforward_gate_v1.py"


def test_margin_walkforward_gate_runs(tmp_path: Path) -> None:
    out = tmp_path / "margin.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out), "--n-folds", "3"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_margin_walkforward_gate_v1"
    assert doc["train_objective"] == "margin_vs_bull"
    assert doc["would_change_active"] is False
    assert len(doc["adaptive_walkforward"]) == 2
    assert doc["global_holdout"]["best"] is not None
