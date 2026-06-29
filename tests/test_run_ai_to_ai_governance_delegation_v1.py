"""Smoke for AI-to-AI governance delegation runner (dry-run only)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_ai_to_ai_governance_delegation_v1.py"
OUT = ROOT / "reports/ai_to_ai_governance_delegation_v1_latest.json"


def test_delegation_dry_run_plan() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("dry_run") is True
    assert "meta_pytest" in (doc.get("auto_lanes_planned") or [])
