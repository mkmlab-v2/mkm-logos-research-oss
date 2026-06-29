#!/usr/bin/env python3
"""Smoke X API credentials + paste files (no submit)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/x_api_readiness_v1_latest.json"
SCRIPT = ROOT / "scripts/post_x_api_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    steps: dict[str, dict] = {}

    paste_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--posts", "2,3,4"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    steps["paste_dry_run"] = {
        "exit_code": paste_proc.returncode,
        "ok": paste_proc.returncode == 0,
        "stdout": paste_proc.stdout.strip()[:500],
        "stderr": paste_proc.stderr.strip()[:300],
    }

    auth_proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--verify-auth", "--posts", "2"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    steps["auth_verify"] = {
        "exit_code": auth_proc.returncode,
        "ok": auth_proc.returncode == 0,
        "stdout": auth_proc.stdout.strip()[:500],
        "stderr": auth_proc.stderr.strip()[:300],
    }

    ok = steps["paste_dry_run"]["ok"] and steps["auth_verify"]["ok"]
    doc = {
        "schema": "x_api_readiness_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "steps": steps,
        "register_hint": (
            "powershell -File scripts\\Invoke-EncryptedSecretStore.ps1 -Action set -Key MKM_X_API_KEY"
        ),
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "steps": {k: v["ok"] for k, v in steps.items()}}, ensure_ascii=False))
    return 0 if ok else (auth_proc.returncode or paste_proc.returncode or 1)


if __name__ == "__main__":
    raise SystemExit(main())
