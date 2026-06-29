"""Invoke-LocalLock P0 smoke — schema + CLI help/list."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "dev_identities_v1.schema.json"
FIXTURE = ROOT / "tests" / "fixtures" / "dev_identities_v1_example.json"


def _run_ps(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            *args,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock P0 is Windows DPAPI scoped")
def test_local_lock_help_exit_zero():
    proc = _run_ps("help")
    assert proc.returncode == 0
    assert "Invoke-LocalLock" in proc.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock P0 is Windows DPAPI scoped")
def test_local_lock_identity_list_json():
    proc = _run_ps("identity", "list")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema"] == "dev_identities_list_v1"
    assert "identities" in payload


def test_dev_identities_fixture_matches_schema():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.validate(instance=fixture, schema=schema)
