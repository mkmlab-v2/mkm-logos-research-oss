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
DEFAULT_OUT = ART / "logos_shadow_weekly_gate_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly Logos shadow quality gate.")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument(
        "--profile",
        choices=("strict", "bootstrap"),
        default="strict",
        help="strict=min_samples 3, bootstrap=min_samples 1 (provisional).",
    )
    ap.add_argument("--min-samples", type=int, default=None)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--min-mean-top1-cosine", type=float, default=0.08)
    ap.add_argument("--max-low-confidence-rate", type=float, default=0.60)
    ap.add_argument("--max-query-error-rate", type=float, default=0.20)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    log_path = args.log_jsonl if args.log_jsonl.is_absolute() else ROOT / args.log_jsonl
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
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

    count = len(rows)
    mean_cos = sum(_f(r.get("mean_top1_cosine")) for r in rows) / count if count else 0.0
    low_conf_count = sum(1 for r in rows if bool(r.get("low_confidence")))
    low_conf_rate = (low_conf_count / count) if count else 1.0
    q_ok = sum(int(r.get("queries_ok") or 0) for r in rows)
    q_err = sum(int(r.get("queries_error") or 0) for r in rows)
    q_total = q_ok + q_err
    q_error_rate = (q_err / q_total) if q_total else 1.0

    required_min_samples = int(args.min_samples) if args.min_samples is not None else (1 if args.profile == "bootstrap" else 3)
    checks = {
        "min_samples_pass": count >= required_min_samples,
        "mean_top1_cosine_pass": mean_cos >= float(args.min_mean_top1_cosine),
        "low_conf_rate_pass": low_conf_rate <= float(args.max_low_confidence_rate),
        "query_error_rate_pass": q_error_rate <= float(args.max_query_error_rate),
    }
    all_pass = all(checks.values())
    decision = "GO" if all_pass else ("WATCH" if checks["min_samples_pass"] else "HOLD")

    out = {
        "schema": "logos_shadow_weekly_gate_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": int(args.window_days),
        "profile": args.profile,
        "window_start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_end_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": {
            "samples": count,
            "mean_top1_cosine_7d": round(mean_cos, 9),
            "low_confidence_rate_7d": round(low_conf_rate, 6),
            "query_error_rate_7d": round(q_error_rate, 6),
            "queries_ok_7d": q_ok,
            "queries_error_7d": q_err,
        },
        "thresholds": {
            "min_samples": required_min_samples,
            "min_mean_top1_cosine": float(args.min_mean_top1_cosine),
            "max_low_confidence_rate": float(args.max_low_confidence_rate),
            "max_query_error_rate": float(args.max_query_error_rate),
        },
        "checks": checks,
        "all_pass": all_pass,
        "decision": decision,
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
            "promotion_to_a_track_allowed": False,
            "provisional_gate": args.profile == "bootstrap",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

