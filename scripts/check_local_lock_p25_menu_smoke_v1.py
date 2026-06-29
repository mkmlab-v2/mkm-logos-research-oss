#!/usr/bin/env python3
"""P2.5 smoke for LocalLock menu + shell alias register script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
ALIAS_PS1 = ROOT / "scripts" / "Register-LocalLockShellAlias_v1.ps1"
OUT = ROOT / "reports" / "local_lock_p25_menu_smoke_v1_latest.json"


def _run_ps(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
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
        input=input_text,
    )


def main() -> int:
    doc: dict = {
        "schema": "local_lock_p25_menu_smoke_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": {},
    }
    ok = True

    doc["checks"]["alias_script_exists"] = {"ok": ALIAS_PS1.is_file()}
    ok = ok and doc["checks"]["alias_script_exists"]["ok"]

    help_proc = _run_ps("help")
    help_text = help_proc.stdout
    help_ok = (
        help_proc.returncode == 0
        and "menu" in help_text.lower()
        and "add <key>" in help_text.lower()
        and "Register-LocalLockShellAlias" in help_text
    )
    doc["checks"]["help_menu_and_alias"] = {"ok": help_ok, "exit_code": help_proc.returncode}
    ok = ok and help_ok

    menu_proc = _run_ps("menu", input_text="6\n")
    menu_ok = menu_proc.returncode == 0 and "interactive menu" in menu_proc.stdout.lower()
    doc["checks"]["menu_exit_six"] = {"ok": menu_ok, "exit_code": menu_proc.returncode}
    ok = ok and menu_ok

    doc["ok"] = ok
    doc["reproduce"] = "py scripts/check_local_lock_p25_menu_smoke_v1.py"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
