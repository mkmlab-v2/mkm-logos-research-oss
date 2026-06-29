"""Smoke: Invoke-MkmMcpCoordinator_v1.ps1 writes schema-valid JSON."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COORD_SCRIPT = ROOT / "scripts" / "Invoke-MkmMcpCoordinator_v1.ps1"
OUT_JSON = ROOT / "reports" / "mkm_mcp_coordinator_v1_latest.json"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_mcp_coordinator_v1.schema.json"
SCHEMA_CHECK = ROOT / "scripts" / "check_mkm_mcp_coordinator_schema_v1.py"


def test_mkm_mcp_coordinator_smoke_v1():
    if not COORD_SCRIPT.is_file():
        pytest.skip("coordinator script missing")

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(COORD_SCRIPT),
        "-Lane",
        "ops",
        "-SkipPluginDiet",
        "-SkipBudgetGate",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=170,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT_JSON.is_file(), "coordinator output missing"

    doc = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm_mcp_coordinator_v1"
    assert doc.get("lane") == "ops"
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("research_only") is True
    assert "inventory" in doc
    assert "reproducible_command" in doc

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)

    if SCHEMA_CHECK.is_file():
        check = subprocess.run(
            [sys.executable, str(SCHEMA_CHECK), "--json", str(OUT_JSON)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert check.returncode == 0, check.stderr or check.stdout
