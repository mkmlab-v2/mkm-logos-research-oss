#!/usr/bin/env python3
"""HTTP verify no1kmedi encounter-sequence API (:3010 or ephemeral dev port) [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/no1kmedi_encounter_sequence_api_http_smoke_v1_latest.json"
ALERTS = ROOT / "reports/tkm_encounter_sequence_http_smoke_alerts_v1.jsonl"
PS1 = ROOT / "projects/no1kmedi/scripts/run-encounter-sequence-http-smoke.ps1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_alert(doc: dict[str, Any]) -> None:
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts_utc": _utc(),
        "http_smoke_ok": doc.get("http_smoke_ok"),
        "exit_code": doc.get("exit_code"),
        "skipped": doc.get("skipped", False),
    }
    with ALERTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def verify(*, skip_http: bool = False) -> dict[str, Any]:
    if skip_http:
        return {
            "schema": "no1kmedi_encounter_sequence_api_http_smoke_v1",
            "generated_at_utc": _utc(),
            "http_smoke_ok": False,
            "skipped": True,
            "send_gate": "HOLD",
            "note_ko": "HTTP smoke skipped (--skip-http)",
        }

    env = os.environ.copy()
    env.setdefault("MKM_WORKSPACE_ROOT", str(ROOT))
    pwsh = "pwsh"
    proc = subprocess.run(
        [pwsh, "-NoProfile", "-File", str(PS1)],
        cwd=ROOT / "projects/no1kmedi",
        capture_output=True,
        text=True,
        env=env,
    )
    stdout = proc.stdout or ""
    http_smoke_ok = proc.returncode == 0 and "OK encounter-sequence HTTP:" in stdout
    return {
        "schema": "no1kmedi_encounter_sequence_api_http_smoke_v1",
        "generated_at_utc": _utc(),
        "http_smoke_ok": http_smoke_ok,
        "exit_code": proc.returncode,
        "stdout_tail": stdout[-800:],
        "stderr_tail": (proc.stderr or "")[-400:],
        "ps1_path": str(PS1).replace("\\", "/"),
        "send_gate": "HOLD",
        "note_ko": "Next dev ephemeral port + POST /api/clinician/encounter-sequence-v1",
        "reproduce": "py scripts/verify_no1kmedi_encounter_sequence_api_http_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-http", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = verify(skip_http=args.skip_http)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_http and not doc.get("http_smoke_ok"):
        _append_alert(doc)
    print(json.dumps({"ok": doc.get("http_smoke_ok"), "skipped": doc.get("skipped", False)}))
    if args.skip_http:
        return 0
    return 0 if doc.get("http_smoke_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
