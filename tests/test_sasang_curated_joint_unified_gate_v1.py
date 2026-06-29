from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_unified_gate_after_drill() -> None:
    drill = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_sasang_curated_joint_promote_drill_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert drill.returncode == 0, drill.stderr
    gate = _ROOT / "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"
    doc = json.loads(gate.read_text(encoding="utf-8-sig"))
    assert doc["gate_ok"] is True
    assert doc["curated_joint_status"] in (
        "dual_idle_hold",
        "csv_ready_to_apply",
        "jsonl_ready_to_apply",
        "dual_ready_to_apply",
        "applied_partial_or_full",
    )
