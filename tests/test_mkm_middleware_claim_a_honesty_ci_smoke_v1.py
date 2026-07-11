"""Claim-A honesty CI smoke — local runnable log for Claude residual."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_mkm_middleware_claim_a_honesty_ci_smoke_v1.py"
OUT = ROOT / "docs/final/artifacts/mkm_middleware_claim_a_honesty_ci_smoke_v1_latest.json"


def test_honesty_ci_smoke_exit_0():
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["schema"] == "mkm_middleware_claim_a_honesty_ci_smoke_v1"
    assert all(s["exit_code"] == 0 for s in doc.get("steps") or [])
