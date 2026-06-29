"""Dry-run only — no upstream billing in CI."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/sandbox/run_chat_shim_upstream_shadow_v1.py"
OUT = ROOT / "reports/chat_shim_upstream_shadow_v1_pytest_dry_latest.json"


def test_upstream_shadow_dry_run_schema():
    proc = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--dry-run",
            "--strict",
            "--out-json",
            str(OUT),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "chat_shim_upstream_shadow_v1"
    assert doc.get("dry_run") is True
