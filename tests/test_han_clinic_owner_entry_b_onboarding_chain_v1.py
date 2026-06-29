"""han_clinic_owner_entry_b_onboarding_chain_v1 — preflight smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
CHAIN = WS / "scripts/run_han_clinic_owner_entry_b_onboarding_chain_v1.py"
OUT = WS / "reports/han_clinic_owner_entry_b_onboarding_chain_v1_latest.json"


def test_entry_b_onboarding_chain_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHAIN)],
        cwd=str(WS),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("ok") is True
    assert doc.get("send_gate") == "HOLD"
