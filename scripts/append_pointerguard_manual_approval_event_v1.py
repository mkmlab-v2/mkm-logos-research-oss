#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
LOG_DEFAULT = ART / "pointerguard_manual_approval_log_latest.json"
OUT_EVENT_DEFAULT = ART / "pointerguard_manual_approval_event_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--action", required=True, help="High-risk action (e.g. unfreeze_ramp, public_scope_expand).")
    ap.add_argument("--approver-1", required=True)
    ap.add_argument("--approver-2", required=True)
    ap.add_argument("--ticket", required=True, help="Approval ticket or evidence reference.")
    ap.add_argument("--justification", default="")
    ap.add_argument("--manual-log-json", type=Path, default=LOG_DEFAULT)
    ap.add_argument("--event-out", type=Path, default=OUT_EVENT_DEFAULT)
    args = ap.parse_args()

    log_path = args.manual_log_json if args.manual_log_json.is_absolute() else ROOT / args.manual_log_json
    out_event_path = args.event_out if args.event_out.is_absolute() else ROOT / args.event_out

    if not log_path.exists():
        raise SystemExit(f"manual approval log missing: {log_path}")
    log_doc = _read_json(log_path)
    if str(log_doc.get("schema")) != "pointerguard_manual_approval_log_v1":
        raise SystemExit("manual approval log schema mismatch")

    policy = log_doc.get("policy", {})
    if not bool(policy.get("manual_promotion_lock", False)):
        raise SystemExit("manual_promotion_lock disabled")
    if not bool(policy.get("requires_two_person_review", False)):
        raise SystemExit("requires_two_person_review disabled")
    if not bool(policy.get("approval_log_required", False)):
        raise SystemExit("approval_log_required disabled")

    a1 = args.approver_1.strip()
    a2 = args.approver_2.strip()
    if not a1 or not a2:
        raise SystemExit("approvers must be non-empty")
    if a1 == a2:
        raise SystemExit("approver-1 and approver-2 must be different")
    ticket = args.ticket.strip()
    if not re.match(r"^[A-Z]+-\d{4}-\d{2}-\d{2}-\d{3,}$", ticket):
        raise SystemExit("ticket format must match PREFIX-YYYY-MM-DD-NNN (e.g. OPS-2026-04-28-001)")

    entry = {
        "approved_at_utc": _now_utc(),
        "action": args.action.strip(),
        "ticket": ticket,
        "approvers": [a1, a2],
        "justification": args.justification.strip(),
    }

    entries = log_doc.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    entries.append(entry)
    log_doc["entries"] = entries
    log_doc["last_event_at_utc"] = entry["approved_at_utc"]
    log_doc["last_event_action"] = entry["action"]

    log_path.write_text(json.dumps(log_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_event = {
        "schema": "pointerguard_manual_approval_event_v1",
        "generated_at_utc": _now_utc(),
        "log_path": str(log_path),
        "entry": entry,
        "entry_count": len(entries),
    }
    out_event_path.parent.mkdir(parents=True, exist_ok=True)
    out_event_path.write_text(json.dumps(out_event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "entry_count": len(entries), "log": str(log_path), "event_out": str(out_event_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
