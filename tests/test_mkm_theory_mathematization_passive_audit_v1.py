"""Theory mathematization passive audit chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_mkm_theory_mathematization_passive_audit_v1.py"
OUT = ROOT / "docs/final/artifacts/mkm_theory_mathematization_passive_audit_v1_latest.json"


def test_passive_audit_skip_mcp_exit0():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-mcp"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_theory_mathematization_passive_audit_v1"
    assert doc["ok"] is True
    assert doc["skip_mcp"] is True
    assert len(doc["steps"]) == 3
