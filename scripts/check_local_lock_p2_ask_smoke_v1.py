#!/usr/bin/env python3
"""P2 smoke for LocalLock ask — deterministic catalog only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
ASK_PY = ROOT / "scripts" / "local_lock_ask_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "dev_identities_v1_example.json"
OUT = ROOT / "reports" / "local_lock_p2_ask_smoke_v1_latest.json"


def _run_ps(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
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
        env=run_env,
    )


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


def main() -> int:
    doc: dict = {
        "schema": "local_lock_p2_ask_smoke_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": {},
    }
    ok = True

    help_proc = _run_ps("help")
    help_ok = help_proc.returncode == 0 and "ask" in help_proc.stdout.lower()
    doc["checks"]["help_ask_subcommand"] = {"ok": help_ok, "exit_code": help_proc.returncode}
    ok = ok and help_ok

    ask_proc = _run_ask("supabase orange test database")
    ask_ok = ask_proc.returncode == 0
    parsed: dict | None = None
    if ask_ok:
        try:
            parsed = json.loads(ask_proc.stdout.strip())
            ask_ok = (
                parsed.get("schema") == "local_lock_ask_v1"
                and parsed.get("resolved_key") == "supabase_dev"
                and parsed.get("secret_plane") == "not_accessed"
            )
        except json.JSONDecodeError:
            ask_ok = False
    doc["checks"]["ask_supabase_fixture"] = {
        "ok": ask_ok,
        "exit_code": ask_proc.returncode,
        "resolver": (parsed or {}).get("resolver"),
    }
    ok = ok and ask_ok

    ps_ask = _run_ps(
        "ask",
        "supabase",
        "dev",
        env={"MKM_LOCAL_LOCK_IDENTITY_FILE": str(FIXTURE)},
    )
    ps_ok = ps_ask.returncode == 0
    if ps_ok:
        try:
            payload = json.loads(ps_ask.stdout.strip())
            ps_ok = payload.get("resolved_key") == "supabase_dev" and payload.get("secret_plane") == "not_accessed"
        except json.JSONDecodeError:
            ps_ok = False
    doc["checks"]["ps1_ask_wrapper"] = {
        "ok": ps_ok,
        "exit_code": ps_ask.returncode,
    }
    ok = ok and ps_ok

    doc["ok"] = ok
    doc["reproduce"] = "py scripts/check_local_lock_p2_ask_smoke_v1.py"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
