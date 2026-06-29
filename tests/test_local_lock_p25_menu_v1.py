"""LocalLock P2.5 — menu and add shorthand."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
ALIAS_PS1 = ROOT / "scripts" / "Register-LocalLockShellAlias_v1.ps1"


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock is Windows-scoped")
def test_help_lists_menu_and_add():
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
    assert "menu" in proc.stdout.lower()
    assert "add <key>" in proc.stdout.lower()


@pytest.mark.skipif(sys.platform != "win32", reason="LocalLock is Windows-scoped")
def test_menu_exits_on_six():
    proc = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
            "menu",
        ],
        cwd=str(ROOT),
        input="6\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "interactive menu" in proc.stdout.lower()


def test_alias_register_script_exists():
    assert ALIAS_PS1.is_file()
