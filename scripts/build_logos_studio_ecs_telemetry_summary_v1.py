#!/usr/bin/env python3
"""Build Logos Studio ECS telemetry summary from JSONL events."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_ts_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_float(value: Any) -> float | None:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num != num:  # NaN guard
        return None
    return num


def _pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return values[0]
    if q >= 1:
        return values[-1]
    idx = q * (len(values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(values) - 1)
    frac = idx - lo
    return values[lo] * (1 - frac) + values[hi] * frac


def _safe_div(a: float, b: float) -> float:
    if b <= 0:
        return 0.0
    return a / b


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--events-jsonl",
        default="memory/commercialization/hub_events.jsonl",
        help="Telemetry source JSONL path (workspace relative).",
    )
    parser.add_argument(
        "--out-json",
        default="docs/final/artifacts/logos_studio_ecs_telemetry_summary_latest.json",
        help="Output summary JSON path (workspace relative).",
    )
    parser.add_argument("--window-days", type=int, default=30, help="Lookback window in days.")
    parser.add_argument("--event-name", default="logos_research_query_success_v1")
    args = parser.parse_args()

    root = _root()
    src = root / args.events_jsonl
    out = root / args.out_json
    now = datetime.now(timezone.utc)
    lower = now - timedelta(days=max(1, args.window_days))

    line_count = 0
    parse_error_count = 0
    event_rows: list[dict[str, Any]] = []
    band_counts = {"low": 0, "mid": 0, "high": 0, "unknown": 0}
    query_mode_counts: dict[str, int] = {}
    access_gate_counts: dict[str, int] = {}
    ecs_values: list[float] = []
    skipped_out_of_window = 0

    if src.is_file():
        with src.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    parse_error_count += 1
                    continue
                if not isinstance(row, dict):
                    parse_error_count += 1
                    continue
                if row.get("event") != args.event_name:
                    continue
                ts = _parse_ts_utc(row.get("ts_utc"))
                if ts is not None and ts < lower:
                    skipped_out_of_window += 1
                    continue
                event_rows.append(row)

                mode = str(row.get("effective_level") or "unknown")[:120]
                query_mode_counts[mode] = query_mode_counts.get(mode, 0) + 1
                gate = str(row.get("access_gate") or "unknown")[:120]
                access_gate_counts[gate] = access_gate_counts.get(gate, 0) + 1

                band = str(row.get("ecs_band") or "unknown").lower()
                if band not in ("low", "mid", "high"):
                    band = "unknown"
                band_counts[band] += 1

                ecs = _to_float(row.get("ecs_v1"))
                if ecs is not None:
                    ecs_values.append(max(0.0, min(100.0, ecs)))

    ecs_values.sort()
    ecs_observed = len(ecs_values)
    event_count = len(event_rows)
    ecs_missing = max(0, event_count - ecs_observed)

    ecs_stats = {
        "count": ecs_observed,
        "min": round(_pct(ecs_values, 0.0), 4),
        "p10": round(_pct(ecs_values, 0.1), 4),
        "median": round(median(ecs_values), 4) if ecs_values else 0.0,
        "mean": round(mean(ecs_values), 4) if ecs_values else 0.0,
        "p90": round(_pct(ecs_values, 0.9), 4),
        "max": round(_pct(ecs_values, 1.0), 4),
    }

    report = {
        "schema": "logos_studio_ecs_telemetry_summary_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": max(1, args.window_days),
        "source": {
            "events_jsonl": _display_path(src, root),
            "source_exists": src.is_file(),
            "line_count": line_count,
            "parse_error_count": parse_error_count,
            "skipped_out_of_window": skipped_out_of_window,
        },
        "event_contract": {
            "event_name": args.event_name,
            "events_in_window": event_count,
            "ecs_observed_count": ecs_observed,
            "ecs_missing_count": ecs_missing,
            "ecs_observed_rate": round(_safe_div(ecs_observed, event_count), 4),
        },
        "ecs_stats": ecs_stats,
        "band_counts": band_counts,
        "query_mode_counts": query_mode_counts,
        "access_gate_counts": access_gate_counts,
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "schema": report["schema"],
                "events_in_window": event_count,
                "ecs_observed_count": ecs_observed,
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
