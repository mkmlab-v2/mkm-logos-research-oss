#!/usr/bin/env python3
"""P1.5 smoke for LocalLock schema, CLI help, and browser helper dry-run."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "Invoke-LocalLock_v1.ps1"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "dev_identities_v1.schema.json"
FIXTURE = ROOT / "tests" / "fixtures" / "dev_identities_v1_example.json"
BROWSER_PY = ROOT / "scripts" / "local_lock_browser_open_v1.py"
OUT = ROOT / "reports" / "local_lock_p15_smoke_v1_latest.json"


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


def _run_py(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BROWSER_PY), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    doc: dict = {
        "schema": "local_lock_p15_smoke_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": {},
    }
    ok = True

    help_proc = _run_ps("help")
    help_ok = help_proc.returncode == 0 and "AutofillEmail" in help_proc.stdout
    doc["checks"]["help_autofill_flag"] = {
        "ok": help_ok,
        "exit_code": help_proc.returncode,
    }
    ok = ok and help_ok

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

    if FIXTURE.is_file() and BROWSER_PY.is_file():
        sample_key = "supabase_dev"
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        row = fixture[sample_key]
        payload = {
            "key": sample_key,
            "login_url": row["login_url"],
            "email": row["email"],
            "browser_tier": row.get("browser_tier", 3),
            "autofill": row.get("autofill", {"mode": "email_only"}),
        }
        tmp = ROOT / "reports" / "_local_lock_p15_dry_meta.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        dry = _run_py("--dry-run", "--meta-file", str(tmp))
        dry_ok = dry.returncode == 0
        secret_leak = "password" in dry.stdout.lower() and "not_passed" not in dry.stdout
        if dry_ok:
            try:
                summary = json.loads(dry.stdout.strip().splitlines()[-1])
                dry_ok = summary.get("secret_plane") == "not_passed"
            except (json.JSONDecodeError, IndexError):
                dry_ok = False
        doc["checks"]["browser_dry_run"] = {
            "ok": dry_ok and not secret_leak,
            "exit_code": dry.returncode,
        }
        ok = ok and doc["checks"]["browser_dry_run"]["ok"]

    deps_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_local_lock_browser_deps_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc["checks"]["browser_deps_probe"] = {
        "ok": deps_proc.returncode in (0, 1),
        "exit_code": deps_proc.returncode,
        "note": "playwright optional; exit 1 when not installed",
    }
    ok = ok and doc["checks"]["browser_deps_probe"]["ok"]

    doc["ok"] = ok
    doc["reproduce"] = "py scripts/check_local_lock_p15_smoke_v1.py"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
