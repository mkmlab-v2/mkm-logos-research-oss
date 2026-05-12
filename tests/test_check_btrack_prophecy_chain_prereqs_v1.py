"""Regression for check_btrack_prophecy_chain_prereqs_v1.py (read-only triage)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_btrack_prophecy_chain_prereqs_v1.py"


def test_prereqs_script_stdout_schema() -> None:
    assert SCRIPT.is_file()
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdout-only"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc.get("schema") == "btrack_prophecy_chain_prereqs_v1"
    assert doc.get("summary")
    checks = doc.get("checks") or []
    assert any(c.get("kind") == "script" for c in checks)
    assert all("path" in c and "ok" in c for c in checks)


def test_prereqs_strict_when_kospi_present_returns_zero() -> None:
    kospi = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
    if not kospi.is_file():
        pytest.skip("KOSPI SSOT CSV not present in this checkout")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdout-only", "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
