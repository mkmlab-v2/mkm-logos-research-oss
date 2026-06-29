"""LocalLock P1.5 — extended schema, help flag, browser dry-run."""

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
BROWSER_PY = ROOT / "scripts" / "local_lock_browser_open_v1.py"


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


def test_dev_identities_p15_fixture_matches_schema():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.validate(instance=fixture, schema=schema)
    assert fixture["supabase_dev"]["browser_tier"] == 3
    assert fixture["supabase_dev"]["autofill"]["mode"] == "email_only"


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock is Windows-scoped")
def test_local_lock_help_mentions_autofill_email():
    proc = _run_ps("help")
    assert proc.returncode == 0
    assert "AutofillEmail" in proc.stdout


def test_browser_helper_dry_run_redacts_secrets():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    row = fixture["supabase_dev"]
    payload = {
        "key": "supabase_dev",
        "login_url": row["login_url"],
        "email": row["email"],
        "browser_tier": row["browser_tier"],
        "autofill": row["autofill"],
    }
    tmp = ROOT / "reports" / "_pytest_local_lock_dry_meta.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(BROWSER_PY), "--dry-run", "--meta-file", str(tmp)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(proc.stdout.strip())
    assert summary["secret_plane"] == "not_passed"
    assert summary["email_present"] is True
