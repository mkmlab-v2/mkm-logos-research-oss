#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
DRILL_HISTORY_DEFAULT = ART / "pointerguard_p0_alert_drill_history_v1.jsonl"
APPROVAL_AUDIT_DEFAULT = ART / "pointerguard_manual_approval_audit_report_latest.json"
FAILURE_TOPN_DEFAULT = ART / "pointerguard_readiness_failure_topn_latest.json"
OUT_DEFAULT = ART / "pointerguard_monthly_maintenance_report_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_dt(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--window-days", type=int, default=31)
    ap.add_argument("--drill-history-jsonl", type=Path, default=DRILL_HISTORY_DEFAULT)
    ap.add_argument("--approval-audit-json", type=Path, default=APPROVAL_AUDIT_DEFAULT)
    ap.add_argument("--failure-topn-json", type=Path, default=FAILURE_TOPN_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    now = _now()
    since = now - timedelta(days=max(1, int(args.window_days)))
    drill_path = args.drill_history_jsonl if args.drill_history_jsonl.is_absolute() else ROOT / args.drill_history_jsonl
    approval_path = args.approval_audit_json if args.approval_audit_json.is_absolute() else ROOT / args.approval_audit_json
    failure_path = args.failure_topn_json if args.failure_topn_json.is_absolute() else ROOT / args.failure_topn_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    drills = _read_jsonl(drill_path)
    live_ok_count = 0
    live_fail_count = 0
    for row in drills:
        dt = _parse_dt(row.get("generated_at_utc"))
        if dt is None or dt < since:
            continue
        if bool(row.get("dry_run", True)):
            continue
        if bool(row.get("ok", False)):
            live_ok_count += 1
        else:
            live_fail_count += 1

    approval = _read_json(approval_path) if approval_path.exists() else {}
    failure = _read_json(failure_path) if failure_path.exists() else {}
    top_repair = (failure.get("repair_queue_topn") or [None])[0]

    out_doc = {
        "schema": "pointerguard_monthly_maintenance_report_v1",
        "generated_at_utc": now.isoformat(),
        "window_days": int(args.window_days),
        "window_since_utc": since.isoformat(),
        "summary": {
            "live_p0_drill_ok_count": live_ok_count,
            "live_p0_drill_fail_count": live_fail_count,
            "approval_events_in_window": int(approval.get("summary", {}).get("events_in_window", 0)),
            "readiness_failed_check_count": int(failure.get("failed_check_count", 0)),
            "top_repair_priority": top_repair,
        },
        "sources": {
            "drill_history_jsonl": str(drill_path),
            "approval_audit_json": str(approval_path),
            "failure_topn_json": str(failure_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "live_p0_drill_ok_count": live_ok_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
