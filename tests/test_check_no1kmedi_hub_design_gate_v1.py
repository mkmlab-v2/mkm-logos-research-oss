"""no1kmedi Hub design gate — discover v3 tokens + shell + live smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_no1kmedi_hub_design_gate_v1.py"
OUT = ROOT / "reports/no1kmedi_hub_design_gate_v1_latest.json"


def test_no1kmedi_hub_design_gate_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE), "--run-design-tokens", "--run-live-smoke"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "no1kmedi_hub_design_gate_v1"
    assert doc.get("ok") is True
    assert doc.get("send_gate") == "HOLD"
    checks = doc.get("checks") or {}
    assert checks.get("css_discover_v3_tokens") is True
    assert checks.get("shell_gate_v2") is True
    assert checks.get("live_hub_smoke") is True
