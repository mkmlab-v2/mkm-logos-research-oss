#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DECISION_LOG = ROOT / "reports" / "agent_decisions_log.jsonl"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "fallback_post_cutoff_watch_report_latest.json"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "fallback_post_cutoff_watch_report_latest.md"

MISSION_ID = "fallback_post_cutoff_watch_v1"
DECISION = "WARN_POST_CUTOFF_RATE_HIGH"
WINDOW_DAYS = 7
DEFAULT_DAILY_RUNS = 1.0
WARN_THRESHOLD = 0.15
CRITICAL_THRESHOLD = 0.35


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def main() -> int:
    now = datetime.now(timezone.utc)
    cutoff_window = now - timedelta(days=WINDOW_DAYS)
    baseline_reset_raw = os.environ.get("FALLBACK_POST_CUTOFF_BASELINE_RESET_UTC", "").strip()
    baseline_reset = _parse_dt(baseline_reset_raw) if baseline_reset_raw else None
    cutoff = cutoff_window if baseline_reset is None else max(cutoff_window, baseline_reset)
    rows: list[dict[str, Any]] = []
    if DECISION_LOG.is_file():
        for line in DECISION_LOG.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if str(obj.get("mission_id") or "") != MISSION_ID:
                continue
            if str(obj.get("decision") or "") != DECISION:
                continue
            ts = _parse_dt(obj.get("timestamp"))
            if ts is None or ts < cutoff:
                continue
            rows.append(obj)

    by_day: Counter[str] = Counter()
    by_actor: Counter[str] = Counter()
    for r in rows:
        ts = _parse_dt(r.get("timestamp"))
        if ts is None:
            continue
        by_day[ts.strftime("%Y-%m-%d")] += 1
        by_actor[str(r.get("actor") or "unknown")] += 1

    out = {
        "schema": "fallback_post_cutoff_watch_report_v1",
        "generated_at_utc": _iso_now(),
        "window_days": WINDOW_DAYS,
        "effective_cutoff_utc": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_reset_utc": baseline_reset.strftime("%Y-%m-%dT%H:%M:%SZ") if isinstance(baseline_reset, datetime) else None,
        "mission_id": MISSION_ID,
        "decision": DECISION,
        "source_log": str(DECISION_LOG.resolve()).replace("\\", "/"),
        "summary": {
            "warn_count": len(rows),
            "days_with_warn": len(by_day),
            "latest_warn_ts_utc": max((_parse_dt(r.get("timestamp")) for r in rows if _parse_dt(r.get("timestamp"))), default=None),
        },
        "by_day": dict(sorted(by_day.items())),
        "by_actor": dict(by_actor),
    }
    latest = out["summary"]["latest_warn_ts_utc"]
    if isinstance(latest, datetime):
        out["summary"]["latest_warn_ts_utc"] = latest.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        out["summary"]["latest_warn_ts_utc"] = None

    expected_runs = max(1.0, WINDOW_DAYS * DEFAULT_DAILY_RUNS)
    warn_rate_7d = float(out["summary"]["warn_count"]) / expected_runs
    if warn_rate_7d >= CRITICAL_THRESHOLD:
        signal = "CRITICAL"
        color = "RED"
    elif warn_rate_7d >= WARN_THRESHOLD:
        signal = "WATCH"
        color = "YELLOW"
    else:
        signal = "GO"
        color = "GREEN"
    out["summary"]["warn_rate_7d"] = round(warn_rate_7d, 6)
    out["summary"]["expected_runs_7d"] = expected_runs
    out["summary"]["signal"] = signal
    out["summary"]["signal_color"] = color
    out["summary"]["signal_thresholds"] = {
        "watch_gte": WARN_THRESHOLD,
        "critical_gte": CRITICAL_THRESHOLD,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md: list[str] = [
        "# Fallback Post-Cutoff Watch Report",
        "",
        f"- window_days: `{WINDOW_DAYS}`",
        f"- baseline_reset_utc: `{out['baseline_reset_utc']}`",
        f"- effective_cutoff_utc: `{out['effective_cutoff_utc']}`",
        f"- warn_count: `{out['summary']['warn_count']}`",
        f"- days_with_warn: `{out['summary']['days_with_warn']}`",
        f"- latest_warn_ts_utc: `{out['summary']['latest_warn_ts_utc']}`",
        f"- warn_rate_7d: `{out['summary']['warn_rate_7d']}`",
        f"- signal: `{out['summary']['signal']}` (`{out['summary']['signal_color']}`)",
        "",
        "## By Day",
    ]
    if out["by_day"]:
        md.extend([f"- `{k}`: {v}" for k, v in out["by_day"].items()])
    else:
        md.append("- none")
    md.extend(["", "## By Actor"])
    if out["by_actor"]:
        md.extend([f"- `{k}`: {v}" for k, v in out["by_actor"].items()])
    else:
        md.append("- none")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
