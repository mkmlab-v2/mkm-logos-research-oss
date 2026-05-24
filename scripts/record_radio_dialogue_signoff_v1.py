#!/usr/bin/env python3
"""Record human sign-off for radio_dialogue_script_v1 before TTS render."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPT = ROOT / "reports" / "radio_dialogue_script_morning_shorts_latest.json"
DEFAULT_OUT = ROOT / "reports" / "radio_dialogue_signoff_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_signoff(
    script_doc: Dict[str, Any],
    *,
    approved_by: str,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "schema": "radio_dialogue_signoff_v1",
        "briefing_id": script_doc.get("briefing_id"),
        "program_style": script_doc.get("program_style"),
        "deployment_target": script_doc.get("deployment_target"),
        "approved": True,
        "approved_by": approved_by,
        "approved_at_utc": _utc_now(),
        "script_generated_at_utc": script_doc.get("generated_at_utc"),
        "notes": notes,
    }


def check_signoff(script_doc: Dict[str, Any], signoff: Dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if signoff.get("schema") != "radio_dialogue_signoff_v1":
        reasons.append("signoff_schema_mismatch")
    if signoff.get("approved") is not True:
        reasons.append("signoff_not_approved")
    if signoff.get("briefing_id") != script_doc.get("briefing_id"):
        reasons.append("briefing_id_mismatch")
    return reasons


def main() -> int:
    ap = argparse.ArgumentParser(description="Record radio dialogue human sign-off.")
    ap.add_argument("--script-json", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--approved-by", type=str, default="commander")
    ap.add_argument("--notes", type=str, default="")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    script_path = args.script_json if args.script_json.is_absolute() else ROOT / args.script_json
    script_doc = _read_json(script_path)
    doc = build_signoff(script_doc, approved_by=args.approved_by, notes=args.notes)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
