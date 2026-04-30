# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.5}
# Balance: 86
# Purpose: Verify chain holds when real resonance input is missing.
# Keywords: pytest, chain, proxy, real, hold
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_survivor_resonance_falsification_chain_v1.py"


def test_chain_holds_without_real_resonance_input(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    proxy_jsonl = ROOT / "docs" / "final" / "artifacts" / "global_atom_survivor_resonance_daily_latest.jsonl"
    missing_real_jsonl = tmp_path / "missing_real.jsonl"
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--proxy-resonance-jsonl",
            str(proxy_jsonl),
            "--real-resonance-jsonl",
            str(missing_real_jsonl),
            "--summary-out",
            str(summary),
            "--proxy-backtest-out",
            str(tmp_path / "proxy_backtest.json"),
            "--proxy-gate-out",
            str(tmp_path / "proxy_gate.json"),
            "--real-backtest-out",
            str(tmp_path / "real_backtest.json"),
            "--real-gate-out",
            str(tmp_path / "real_gate.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(summary.read_text(encoding="utf-8-sig"))
    assert doc["inputs"]["real_resonance_available"] is False
    assert doc["result"]["final_decision"] == "HOLD_RESEARCH_ONLY"

