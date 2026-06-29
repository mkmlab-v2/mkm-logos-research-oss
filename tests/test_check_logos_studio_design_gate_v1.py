"""Logos Research Studio design gate — token SSOT + Playwright smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_logos_studio_design_gate_v1.py"
OUT = ROOT / "reports/logos_studio_design_gate_v1_latest.json"


def test_logos_studio_design_gate_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_studio_design_gate_v1"
    assert doc.get("ok") is True
    assert doc.get("send_gate") == "HOLD"
    checks = doc.get("checks") or {}
    assert checks.get("css_token_ssot") is True
    assert checks.get("playwright_smoke_ok") is True
