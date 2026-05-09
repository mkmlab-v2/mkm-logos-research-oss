#!/usr/bin/env python3
"""Append chronicle weekly alert status to human-gate ledger (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_alert = root / "docs" / "final" / "artifacts" / "chronicle_history_news_weekly_alert_latest.json"
    default_ledger_jsonl = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_ledger_latest.jsonl"
    default_summary = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_ledger_summary_latest.json"

    ap = argparse.ArgumentParser(description="Update chronicle human-gate ledger from weekly alert.")
    ap.add_argument("--alert-json", default=str(default_alert))
    ap.add_argument("--ledger-jsonl", default=str(default_ledger_jsonl))
    ap.add_argument("--summary-json", default=str(default_summary))
    args = ap.parse_args()

    now = _iso_now()
    alert_doc = _read_json(Path(args.alert_json))
    severity = str(alert_doc.get("severity", "UNKNOWN"))
    warning_failures = alert_doc.get("warning_failures") or []
    critical_failures = alert_doc.get("critical_failures") or []
    failures = alert_doc.get("failures") or []
    dispatch = alert_doc.get("dispatch") if isinstance(alert_doc.get("dispatch"), dict) else {}

    row = {
        "schema": "chronicle_human_gate_ledger_row_v1",
        "recorded_at_utc": now,
        "source_track": "B",
        "governance_state": "S1_SHADOW",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "severity": severity,
        "warning_failures": warning_failures,
        "critical_failures": critical_failures,
        "failures": failures,
        "human_review_required": bool(warning_failures or critical_failures),
        "dispatch_status": dispatch.get("status"),
    }
    _append_jsonl(Path(args.ledger_jsonl), row)

    summary = {
        "schema": "chronicle_human_gate_ledger_summary_v1",
        "updated_at_utc": now,
        "latest_severity": severity,
        "latest_human_review_required": row["human_review_required"],
        "latest_warning_failure_count": len(warning_failures),
        "latest_critical_failure_count": len(critical_failures),
        "latest_dispatch_status": dispatch.get("status"),
        "ledger_jsonl": str(Path(args.ledger_jsonl)),
    }
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
