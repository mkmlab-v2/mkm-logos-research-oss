"""Smoke: agent-extract gate runs and cc_005 fails without must_keep (documents manual A/B)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agent_extract_gate_runs() -> None:
    out = ROOT / "reports/cursor_coding_agent_extract_gate_v1_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_cursor_coding_agent_extract_gate_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "cursor_coding_agent_extract_gate_v1"
    cc005 = next((c for c in doc.get("cases", []) if c.get("id") == "cc_005"), None)
    assert cc005 is not None
    assert cc005.get("pass") is True
    assert proc.returncode == 0
