#!/usr/bin/env python3
"""P0 smoke for Invoke-LocalLock_v1.ps1 — no secrets required."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "dev_identities_v1.schema.json"
FIXTURE = ROOT / "tests" / "fixtures" / "dev_identities_v1_example.json"
OUT = ROOT / "reports" / "local_lock_p0_smoke_v1_latest.json"


def _run_ps(args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(PS1),
        *args,
    ]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)


def main() -> int:
    doc: dict = {
        "schema": "local_lock_p0_smoke_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": {},
    }
    ok = True

    if not PS1.is_file():
        doc["checks"]["ps1_exists"] = {"ok": False, "path": str(PS1)}
        ok = False
    else:
        doc["checks"]["ps1_exists"] = {"ok": True, "path": str(PS1)}

    help_proc = _run_ps(["help"])
    doc["checks"]["help_exit_0"] = {
        "ok": help_proc.returncode == 0,
        "exit_code": help_proc.returncode,
    }
    ok = ok and help_proc.returncode == 0

    list_proc = _run_ps(["identity", "list"])
    doc["checks"]["identity_list_exit_0"] = {
        "ok": list_proc.returncode == 0,
        "exit_code": list_proc.returncode,
    }
    ok = ok and list_proc.returncode == 0
    if list_proc.stdout.strip():
        try:
            payload = json.loads(list_proc.stdout)
            doc["checks"]["identity_list_json"] = {
                "ok": payload.get("schema") == "dev_identities_list_v1",
            }
            ok = ok and doc["checks"]["identity_list_json"]["ok"]
        except json.JSONDecodeError:
            doc["checks"]["identity_list_json"] = {"ok": False, "error": "invalid_json"}
            ok = False

    schema_ok = SCHEMA.is_file() and FIXTURE.is_file()
    doc["checks"]["fixture_files"] = {"ok": schema_ok}
    ok = ok and schema_ok

    if schema_ok:
        try:
            import jsonschema  # type: ignore

            schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
            fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
            jsonschema.validate(instance=fixture, schema=schema)
            doc["checks"]["fixture_schema_validate"] = {"ok": True}
        except Exception as exc:  # noqa: BLE001
            doc["checks"]["fixture_schema_validate"] = {"ok": False, "error": str(exc)[:300]}
            ok = False

    doc["ok"] = ok
    doc["reproduce"] = "py scripts/check_local_lock_p0_smoke_v1.py"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
