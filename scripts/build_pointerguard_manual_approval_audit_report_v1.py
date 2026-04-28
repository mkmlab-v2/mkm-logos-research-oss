#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
LOG_DEFAULT = ART / "pointerguard_manual_approval_log_latest.json"
OUT_DEFAULT = ART / "pointerguard_manual_approval_audit_report_latest.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_dt(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manual-log-json", type=Path, default=LOG_DEFAULT)
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    log_path = args.manual_log_json if args.manual_log_json.is_absolute() else ROOT / args.manual_log_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    doc = _read_json(log_path)
    if str(doc.get("schema")) != "pointerguard_manual_approval_log_v1":
        raise SystemExit("manual approval log schema mismatch")

    now = _now_utc()
    since = now - timedelta(days=max(1, int(args.window_days)))
    entries = doc.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    scoped: list[dict[str, Any]] = []
    ticket_missing = 0
    invalid_approver_count = 0
    for e in entries:
        if not isinstance(e, dict):
            continue
        dt = _parse_dt(str(e.get("approved_at_utc", "")))
        if dt is None:
            continue
        if dt < since:
            continue
        ticket = str(e.get("ticket", "")).strip()
        if not ticket:
            ticket_missing += 1
        approvers = e.get("approvers", [])
        if not isinstance(approvers, list) or len(approvers) != 2 or str(approvers[0]) == str(approvers[1]):
            invalid_approver_count += 1
        scoped.append(e)

    action_counter = Counter(str(e.get("action", "unknown")) for e in scoped)
    out_doc = {
        "schema": "pointerguard_manual_approval_audit_report_v1",
        "generated_at_utc": now.isoformat(),
        "window_days": int(args.window_days),
        "window_since_utc": since.isoformat(),
        "summary": {
            "events_in_window": len(scoped),
            "ticket_missing_count": ticket_missing,
            "invalid_two_person_approver_count": invalid_approver_count,
        },
        "actions_top": [{"action": k, "count": v} for k, v in action_counter.most_common(10)],
        "source": {"manual_log_json": str(log_path)},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "events_in_window": len(scoped)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
