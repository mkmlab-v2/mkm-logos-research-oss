"""P2 Phase1 vs Moirai dual-leg compare smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_phase1_moirai_compare() -> None:
    out = ROOT / "reports/prophecy_protocol_phase1_moirai_dual_leg_compare_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/merge_prophecy_protocol_phase1_moirai_dual_leg_v1.py")],
            cwd=str(ROOT),
            timeout=60,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_protocol_phase1_moirai_dual_leg_compare_v1"
    assert doc.get("ok") is True
    rows = {r["row_id"]: r for r in doc.get("rows") or []}
    assert rows["moirai2_dual_leg_pooled"].get("hr") is not None
    assert rows["quant_arm_a_science_sasang"].get("hr") is not None
