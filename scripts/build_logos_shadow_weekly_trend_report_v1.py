#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_LOG = REPORTS / "logos_shadow_daily_metrics_log_v1.jsonl"
DEFAULT_OUT_JSON = ART / "logos_shadow_weekly_trend_report_latest.json"
DEFAULT_OUT_MD = ART / "logos_shadow_weekly_trend_report_latest.md"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(num: float, den: float) -> float:
    return (num / den) if den > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly trend report for Logos shadow metrics.")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    log_path = args.log_jsonl if args.log_jsonl.is_absolute() else ROOT / args.log_jsonl
    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    if not log_path.is_file():
        raise SystemExit(f"Missing log jsonl: {log_path}")

    now = _now()
    start = now - timedelta(days=int(args.window_days))
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(row.get("generated_at_utc"))
        if ts is None or ts < start or ts > now:
            continue
        rows.append(row)

    rows.sort(key=lambda r: str(r.get("generated_at_utc") or ""))
    samples = len(rows)

    mean_values = [_f(r.get("mean_top1_cosine"), 0.0) for r in rows]
    low_conf_values = [1.0 if bool(r.get("low_confidence")) else 0.0 for r in rows]
    error_rates: list[float] = []
    total_ok = 0
    total_err = 0
    for row in rows:
        q_ok = int(row.get("queries_ok") or 0)
        q_err = int(row.get("queries_error") or 0)
        total_ok += q_ok
        total_err += q_err
        error_rates.append(_pct(float(q_err), float(q_ok + q_err)))

    avg_mean = sum(mean_values) / samples if samples else 0.0
    avg_low_conf = sum(low_conf_values) / samples if samples else 0.0
    avg_error_rate = sum(error_rates) / samples if samples else 0.0
    agg_query_error_rate = _pct(float(total_err), float(total_ok + total_err))

    first_mean = mean_values[0] if mean_values else 0.0
    last_mean = mean_values[-1] if mean_values else 0.0
    first_low_conf = low_conf_values[0] if low_conf_values else 0.0
    last_low_conf = low_conf_values[-1] if low_conf_values else 0.0
    first_error_rate = error_rates[0] if error_rates else 0.0
    last_error_rate = error_rates[-1] if error_rates else 0.0

    payload = {
        "schema": "logos_shadow_weekly_trend_report_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": int(args.window_days),
        "window_start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_end_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "samples": samples,
        "series": {
            "mean_top1_cosine": [round(v, 9) for v in mean_values],
            "low_conf_rate_daily": [round(v, 6) for v in low_conf_values],
            "query_error_rate_daily": [round(v, 6) for v in error_rates],
        },
        "summary": {
            "mean_top1_cosine_7d_avg": round(avg_mean, 9),
            "mean_top1_cosine_7d_min": round(min(mean_values), 9) if mean_values else 0.0,
            "mean_top1_cosine_7d_max": round(max(mean_values), 9) if mean_values else 0.0,
            "mean_top1_cosine_delta_first_to_last": round(last_mean - first_mean, 9),
            "low_conf_rate_7d_avg": round(avg_low_conf, 6),
            "low_conf_rate_delta_first_to_last": round(last_low_conf - first_low_conf, 6),
            "query_error_rate_7d_avg": round(avg_error_rate, 6),
            "query_error_rate_7d_aggregate": round(agg_query_error_rate, 6),
            "query_error_rate_delta_first_to_last": round(last_error_rate - first_error_rate, 6),
            "queries_ok_7d": total_ok,
            "queries_error_7d": total_err,
        },
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
            "promotion_to_a_track_allowed": False,
        },
        "evidence_path": str(log_path.resolve()),
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "## Logos Shadow Weekly Trend",
        f"- `window_days`: `{payload['window_days']}`",
        f"- `samples`: `{payload['samples']}`",
        f"- `mean_top1_cosine_7d_avg`: `{payload['summary']['mean_top1_cosine_7d_avg']}`",
        f"- `low_conf_rate_7d_avg`: `{payload['summary']['low_conf_rate_7d_avg']}`",
        f"- `query_error_rate_7d_avg`: `{payload['summary']['query_error_rate_7d_avg']}`",
        f"- `query_error_rate_7d_aggregate`: `{payload['summary']['query_error_rate_7d_aggregate']}`",
        f"- `delta_mean_top1_first_to_last`: `{payload['summary']['mean_top1_cosine_delta_first_to_last']}`",
        f"- `delta_low_conf_first_to_last`: `{payload['summary']['low_conf_rate_delta_first_to_last']}`",
        f"- `delta_query_error_first_to_last`: `{payload['summary']['query_error_rate_delta_first_to_last']}`",
        "- `policy`: `SHADOW_ONLY_NON_GATING`",
    ]
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
