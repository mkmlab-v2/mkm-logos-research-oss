"""Promotion gate smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_promotion_gate_with_commander_ack():
    proc = subprocess.run(
        [sys.executable, "scripts/run_sasang_ablation_promotion_gate_v1.py", "--commander-ack"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    signoff = json.loads((ROOT / "reports/sasang_ablation_matrix_signoff_v1.json").read_text(encoding="utf-8"))
    assert signoff["promotion_ready"] is True
    assert signoff["merge_allowed"] is True
    assert signoff["track_a_promotion_allowed"] is False
    assert signoff["send_gate"] == "HOLD"
