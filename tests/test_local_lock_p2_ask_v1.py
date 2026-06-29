"""LocalLock P2 ask — deterministic key resolution without secrets."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASK_PY = ROOT / "scripts" / "local_lock_ask_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "dev_identities_v1_example.json"
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"


def _run_ask(query: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ASK_PY),
            "--query",
            query,
            "--skip-ollama",
            "--catalog-file",
            str(FIXTURE),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_ask_resolves_supabase_alias():
    proc = _run_ask("수파베이스 테스트 DB")
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["resolved_key"] == "supabase_dev"
    assert doc["secret_plane"] == "not_accessed"
    assert doc["resolver"] == "symbolic_fallback"


def test_ask_no_match_returns_exit_one():
    proc = _run_ask("nonexistent service xyz123")
    assert proc.returncode == 1
    doc = json.loads(proc.stdout)
    assert doc.get("resolved_key") is None


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock PS1 wrapper is Windows-scoped")
def test_ps1_help_lists_ask():
    proc = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            "help",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "ask" in proc.stdout.lower()
