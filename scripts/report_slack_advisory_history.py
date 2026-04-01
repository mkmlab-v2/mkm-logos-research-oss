#!/usr/bin/env python3
"""Aggregate advisory decision history from Slack delivery log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "fact_safe_slack_delivery_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "slack_advisory_history_latest.json"


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _safe_dt_iso(val: Any) -> datetime | None:
    if not isinstance(val, str) or not val.strip():
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None


def _decision_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        v = row.get(key)
        if isinstance(v, dict):
            dec = str(v.get("decision") or "unknown")
        else:
            dec = str(v or "unknown")
        out[dec] = out.get(dec, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.output)
    days = max(1, int(args.days))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    rows = _read_rows(log_path)
    recent: list[dict[str, Any]] = []
    for row in rows:
        dt = _safe_dt_iso(row.get("ts_utc"))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            recent.append(row)

    sent_count = sum(1 for r in recent if bool(r.get("sent")))
    dry_run_count = sum(1 for r in recent if bool(r.get("dry_run")))
    fallback_alert_count = sum(1 for r in recent if bool(r.get("net_source_fallback_alert")))

    dual_counts = _decision_counts(recent, "dual_regime_state_advisory")
    override_counts = _decision_counts(recent, "auto_hold_override_advisory")
    override_decision_counts = _decision_counts(recent, "auto_hold_override_advisory_decision")

    report = {
        "schema": "slack_advisory_history_v1",
        "generated_at_utc": now.isoformat(),
        "log_path": str(log_path),
        "window_days": days,
        "rows_total": len(rows),
        "rows_in_window": len(recent),
        "sent_count": sent_count,
        "dry_run_count": dry_run_count,
        "net_source_fallback_alert_count": fallback_alert_count,
        "dual_regime_state_advisory_decision_counts": dual_counts,
        "auto_hold_override_advisory_decision_counts": override_counts,
        "auto_hold_override_advisory_decision_key_counts": override_decision_counts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

