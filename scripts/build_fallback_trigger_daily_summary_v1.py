#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "fallback_trigger_event_log_v1.jsonl"
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "fallback_trigger_daily_summary_latest.json"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "fallback_trigger_daily_summary_latest.md"


def _parse_ts(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _compute_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    triggered_rows = [
        r
        for r in rows
        if bool(
            r.get("triggered", False)
            or r.get("fallback_safe_triggered", False)
            or r.get("fallback_triggered", False)
        )
    ]
    trig_n = len(triggered_rows)
    trigger_rate = (trig_n / total) if total > 0 else 0.0

    reason_counter: Counter[str] = Counter()
    for r in triggered_rows:
        reasons = r.get("reasons")
        if reasons is None:
            reasons = r.get("fallback_reasons")
        if reasons is None:
            reasons = r.get("trigger_reasons")
        if isinstance(reasons, list):
            for x in reasons:
                reason_counter[str(x)] += 1
        elif isinstance(reasons, str) and reasons.strip():
            reason_counter[reasons.strip()] += 1

    tier_counter: Counter[str] = Counter(str(r.get("tier") or r.get("request_tier") or "unknown") for r in rows)
    top3 = [{"reason": k, "count": v} for k, v in reason_counter.most_common(3)]
    return {
        "total_requests_observed": total,
        "fallback_triggered_count": trig_n,
        "fallback_trigger_rate": round(trigger_rate, 6),
        "top_reasons": top3,
        "tier_distribution": dict(tier_counter),
    }


def main() -> int:
    log_path = Path(os.environ.get("FALLBACK_TRIGGER_EVENT_LOG_PATH", "")).resolve() if os.environ.get("FALLBACK_TRIGGER_EVENT_LOG_PATH", "").strip() else DEFAULT_LOG
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    post_cutoff_raw = os.environ.get("FALLBACK_TRIGGER_CUTOFF_UTC", "").strip()
    post_cutoff = _parse_ts(post_cutoff_raw) if post_cutoff_raw else None

    rows: list[dict[str, Any]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            ts = _parse_ts(str(obj.get("ts_utc", "")))
            if ts is None or ts < cutoff:
                continue
            rows.append(obj)

    stats = _compute_stats(rows)

    payload = {
        "schema": "fallback_trigger_daily_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": 24,
        "source_log": str(log_path.resolve()).replace("\\", "/"),
        **stats,
    }
    if post_cutoff is not None:
        cutoff_rows = [r for r in rows if (_parse_ts(str(r.get("ts_utc", ""))) or cutoff) >= post_cutoff]
        payload["post_cutoff_utc"] = post_cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        payload["post_cutoff_summary"] = _compute_stats(cutoff_rows)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Fallback Trigger Daily Summary",
        "",
        f"- total_requests_observed: `{payload['total_requests_observed']}`",
        f"- fallback_triggered_count: `{payload['fallback_triggered_count']}`",
        f"- fallback_trigger_rate: `{payload['fallback_trigger_rate']}`",
        "",
        "## Top Reasons",
    ]
    if payload["top_reasons"]:
        md.extend(f"- `{r['reason']}`: {r['count']}" for r in payload["top_reasons"])
    else:
        md.append("- none")
    md.extend(["", "## Tier Distribution"])
    if payload["tier_distribution"]:
        md.extend(f"- `{k}`: {v}" for k, v in payload["tier_distribution"].items())
    else:
        md.append("- none")
    if "post_cutoff_summary" in payload:
        pcs = payload["post_cutoff_summary"]
        md.extend(
            [
                "",
                "## Post Cutoff Summary",
                f"- post_cutoff_utc: `{payload['post_cutoff_utc']}`",
                f"- total_requests_observed: `{pcs['total_requests_observed']}`",
                f"- fallback_triggered_count: `{pcs['fallback_triggered_count']}`",
                f"- fallback_trigger_rate: `{pcs['fallback_trigger_rate']}`",
            ]
        )
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
