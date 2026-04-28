#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_manual_approval_log_latest.json"
SECURITY_DEFAULT = ART / "pointerguard_security_hardening_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--security-json", type=Path, default=SECURITY_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    sec_path = args.security_json if args.security_json.is_absolute() else ROOT / args.security_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    lock_enabled = True
    two_person = True
    approval_log_required = True
    if sec_path.exists():
        try:
            doc = _read_json(sec_path)
            control = doc.get("controls", {}).get("manual_promotion_lock", {})
            policy = control.get("policy", {})
            lock_enabled = bool(policy.get("manual_promotion_lock", True))
            two_person = bool(policy.get("requires_two_person_review", True))
            approval_log_required = bool(policy.get("approval_log_required", True))
        except Exception:
            pass

    existing_entries: list[dict[str, Any]] = []
    last_event_at = None
    last_event_action = None
    if out_path.exists():
        try:
            existing = _read_json(out_path)
            if str(existing.get("schema")) == "pointerguard_manual_approval_log_v1":
                raw_entries = existing.get("entries", [])
                if isinstance(raw_entries, list):
                    existing_entries = [e for e in raw_entries if isinstance(e, dict)]
                last_event_at = existing.get("last_event_at_utc")
                last_event_action = existing.get("last_event_action")
        except Exception:
            pass

    out_doc = {
        "schema": "pointerguard_manual_approval_log_v1",
        "generated_at_utc": _now_utc(),
        "policy": {
            "manual_promotion_lock": lock_enabled,
            "requires_two_person_review": two_person,
            "approval_log_required": approval_log_required,
        },
        "entries": existing_entries,
        "entry_count": len(existing_entries),
        "last_event_at_utc": last_event_at,
        "last_event_action": last_event_action,
        "notes": [
            "High-risk actions (e.g. unfreeze ramp, public scope expansion) must append an approval event with two approvers.",
            "Approval entries are preserved across daily refreshes.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "manual_promotion_lock": lock_enabled}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
