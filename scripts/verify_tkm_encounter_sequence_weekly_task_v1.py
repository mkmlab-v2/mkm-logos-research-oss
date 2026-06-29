#!/usr/bin/env python3
"""Verify TKM encounter_sequence weekly scheduled task registration."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_weekly_task_verify_v1_latest.json"
TASK_NAME = "MKM-TkmEncounterSequence-Weekly"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify(*, require_registered: bool = True) -> dict:
    proc = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"],
        capture_output=True,
        text=True,
    )
    registered = proc.returncode == 0
    stdout = proc.stdout or ""
    ready = "Ready" in stdout or "Running" in stdout
    doc = {
        "schema": "tkm_encounter_sequence_weekly_task_verify_v1",
        "generated_at_utc": _utc(),
        "task_name": TASK_NAME,
        "registered": registered,
        "state_ready_or_running": ready if registered else False,
        "verify_ok": registered if require_registered else True,
        "stdout_tail": stdout[-600:],
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--allow-unregistered", action="store_true")
    args = ap.parse_args()
    doc = verify(require_registered=not args.allow_unregistered)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["verify_ok"], "registered": doc["registered"]}))
    return 0 if doc["verify_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
