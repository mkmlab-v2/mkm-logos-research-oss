"""Invoke-LocalLock P1 run — isolated child env injection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
PROBE_KEY = "local_lock_probe"
PROBE_ENV = "LOCAL_LOCK_PROBE"
PROBE_VALUE = "probe-secret-not-for-chat"


def _run_ps(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
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
        env=env,
    )


def _write_identity_only(appdata: Path) -> dict[str, str]:
    mkm = appdata / "MKM"
    mkm.mkdir(parents=True, exist_ok=True)
    identity = {
        PROBE_KEY: {
            "account_class": "testing",
            "email": "probe@example.com",
            "login_url": "https://example.com/login",
            "env_var_name": PROBE_ENV,
        }
    }
    (mkm / "dev_identities_v1.json").write_text(
        json.dumps(identity, indent=2),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["APPDATA"] = str(appdata)
    return env



@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock P1 run is Windows DPAPI scoped")
def test_local_lock_run_requires_double_dash(tmp_path: Path):
    env = _write_identity_only(tmp_path / "Roaming")
    proc = _run_ps(env, "run", PROBE_KEY, "py", "-c", "print(1)")
    assert proc.returncode != 0
    assert "requires '::'" in (proc.stdout + proc.stderr)


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock P1 run is Windows DPAPI scoped")
def test_local_lock_run_child_receives_secret_env(tmp_path: Path):
    appdata = tmp_path / "Roaming"
    env = _write_identity_only(appdata)
    py_code = (
        "import os,sys;"
        f"sys.exit(0 if os.environ.get({PROBE_ENV!r})=={PROBE_VALUE!r} else 2)"
    )
    store_path = appdata / "MKM" / "secret_store_v1.json"
    e2e_cmd = (
        f"$env:APPDATA = '{appdata}'; "
        f"$plain = '{PROBE_VALUE}'; "
        f"$secure = ConvertTo-SecureString $plain -AsPlainText -Force; "
        f"$cipher = ConvertFrom-SecureString $secure; "
        f"$store = @{{ '{PROBE_KEY}' = @{{ encrypted = $cipher; updated_utc = (Get-Date).ToUniversalTime().ToString('o') }} }}; "
        f"$store | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath '{store_path}' -Encoding UTF8; "
        f"& '{PS1}' run {PROBE_KEY} :: py -c \"{py_code}\""
    )
    proc = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            e2e_cmd,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if proc.returncode != 0 and "ConvertTo-SecureString" in (proc.stderr or ""):
        pytest.skip("DPAPI unavailable in pytest subprocess context")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert PROBE_VALUE not in proc.stdout
    assert PROBE_VALUE not in proc.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock P1 run is Windows DPAPI scoped")
def test_local_lock_help_documents_run():
    proc = _run_ps(os.environ.copy(), "help")
    assert proc.returncode == 0
    assert "run <key> ::" in proc.stdout
