#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOG = ROOT / "reports" / "macro_risk" / "forward" / "macro_risk_forward_log_v1.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "macro_risk_forward_weekly_report_latest.json"


def _parse_iso_utc(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build weekly summary report from macro risk forward log.")
    p.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p.add_argument("--window-days", type=int, default=7)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    log_path = args.log_jsonl if args.log_jsonl.is_absolute() else (ROOT / args.log_jsonl)
    out_path = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    window_days = max(1, int(args.window_days))

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    rows = _load_jsonl(log_path)
    in_window: list[dict[str, Any]] = []

    for r in rows:
        ts = str(r.get("logged_at_utc") or "")
        dt = _parse_iso_utc(ts)
        if dt is None:
            continue
        if dt >= cutoff:
            in_window.append(r)

    counts = {"GO": 0, "WATCH": 0, "HOLD": 0, "OTHER": 0}
    risk_levels: dict[str, int] = {}
    for r in in_window:
        state = str(r.get("decision_state") or "").upper()
        if state in counts:
            counts[state] += 1
        else:
            counts["OTHER"] += 1
        level = str(r.get("risk_warning_level") or "unknown").lower()
        risk_levels[level] = risk_levels.get(level, 0) + 1

    latest = in_window[-1] if in_window else (rows[-1] if rows else None)
    report = {
        "schema": "macro_risk_forward_weekly_report_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "log_path": str(log_path),
        "window_days": window_days,
        "rows_total": len(rows),
        "rows_in_window": len(in_window),
        "decision_state_counts": counts,
        "risk_warning_level_counts": risk_levels,
        "latest_row": latest,
        "note": "Forward-only evidence summary. Use with prereg lock hash for audit context.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"forward_weekly_report: PASS -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

