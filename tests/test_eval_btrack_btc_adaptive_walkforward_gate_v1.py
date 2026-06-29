"""Tests for eval_btrack_btc_adaptive_walkforward_gate_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_btrack_btc_adaptive_walkforward_gate_v1.py"


def test_adaptive_walkforward_gate_runs(tmp_path: Path) -> None:
    out = tmp_path / "adaptive.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out), "--n-folds", "3"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_btc_adaptive_walkforward_gate_v1"
    assert doc["research_only"] is True
    assert doc["would_change_active"] is False
    assert len(doc["families"]) == 2
    for fam in doc["families"]:
        assert fam["total_folds"] >= 1
        assert "mean_test_delta_oos" in fam
