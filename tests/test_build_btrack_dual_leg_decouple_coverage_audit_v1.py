"""Smoke test for dual-leg decouple coverage audit."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dual_leg_coverage_audit() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_btrack_dual_leg_decouple_coverage_audit_v1.py")],
        cwd=str(ROOT),
        check=False,
    )
    assert cp.returncode == 0
    doc = json.loads(
        (ROOT / "reports/btrack_dual_leg_decouple_coverage_audit_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["schema"] == "btrack_dual_leg_decouple_coverage_audit_v1"
    assert len(doc.get("panels") or []) == 2
