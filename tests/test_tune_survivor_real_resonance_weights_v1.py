# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 85
# Purpose: Smoke test tuning script output contract.
# Keywords: pytest, tuning, weights, resonance
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tune_survivor_real_resonance_weights_v1.py"


def test_tuning_writes_artifact(tmp_path: Path) -> None:
    out = tmp_path / "tuning.json"
    real_jsonl = tmp_path / "real.jsonl"
    real_backtest = tmp_path / "real_backtest.json"
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--output",
            str(out),
            "--real-jsonl",
            str(real_jsonl),
            "--real-backtest",
            str(real_backtest),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "btrack_survivor_real_resonance_tuning_v1"
    assert isinstance(doc.get("best"), dict)
    assert len(doc.get("rows") or []) > 0

