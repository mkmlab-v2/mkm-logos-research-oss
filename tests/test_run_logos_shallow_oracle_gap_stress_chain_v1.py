"""Shallow oracle gap stress chain smoke (skip Ollama)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts/run_logos_shallow_oracle_gap_stress_chain_v1.py"


def test_shallow_oracle_gap_stress_skip_ollama(tmp_path: Path) -> None:
    out = tmp_path / "chain.json"
    bench = tmp_path / "bench.json"
    gap = tmp_path / "gap.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--skip-ollama",
            "--out",
            str(out),
            "--bench-out",
            str(bench),
            "--gap-out",
            str(gap),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_shallow_oracle_gap_stress_chain_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["all_ok"] is True
    assert doc["fixture_count"] == 32
