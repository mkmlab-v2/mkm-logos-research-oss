"""Smoke tests for outer_lens_rag_dryrun_gate (read-only path checks)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_outer_lens_dryrun_gate_readonly_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_outer_lens_rag_dryrun_gate_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr
    out = ROOT / "docs/final/artifacts/outer_lens_rag_dryrun_gate_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "outer_lens_rag_dryrun_gate_v1"
    assert doc.get("research_only") is True
    assert doc.get("isolation_ok") is True
    assert "track_a_isolation" in doc.get("sections", {})
    assert doc["coordinator_contract_summary"]["naming"]
