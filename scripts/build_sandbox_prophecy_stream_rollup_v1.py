#!/usr/bin/env python3
"""Roll up SANDBOX stream JSONL into per-target time series + watchlist (research_only)."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STREAM = ROOT / "reports/sandbox_prophecy_stream_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_rollup_v1_latest.json"
DEFAULT_WATCHLIST = ROOT / "reports/sandbox_prophecy_watchlist_v1_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _day(ts: str) -> str:
    return str(ts or "")[:10]


def _row_calendar_day(row: dict[str, Any]) -> str:
    explicit = row.get("snapshot_calendar_date_utc")
    if explicit:
        return str(explicit)[:10]
    return _day(str(row.get("generated_at_utc") or ""))


def _hit(row: dict[str, Any]) -> float | None:
    m = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    try:
        return float(m.get("price_directional_hit_rate"))
    except (TypeError, ValueError):
        return None


def _dedupe_latest_per_day(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    """target_id -> day -> row (latest ts wins)."""
    bucket: dict[str, dict[str, tuple[str, dict[str, Any]]]] = defaultdict(dict)
    for r in rows:
        tid = str(r.get("target_id") or "")
        if not tid or not r.get("ok"):
            continue
        day = _row_calendar_day(r)
        if not day:
            continue
        ts = str(r.get("generated_at_utc") or "")
        prev = bucket[tid].get(day)
        if prev is None or ts > prev[0]:
            bucket[tid][day] = (ts, r)
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for tid, days in bucket.items():
        out[tid] = {d: pair[1] for d, pair in days.items()}
    return out


def _consecutive_pass_streak(daily_hits: list[tuple[str, float]], *, threshold: float) -> int:
    streak = 0
    for _, h in reversed(daily_hits):
        if h >= threshold:
            streak += 1
        else:
            break
    return streak


def build_rollup(
    stream_rows: list[dict[str, Any]],
    *,
    watchlist_hit_threshold: float = 0.55,
    watchlist_streak_days: int = 3,
    rolling_windows: tuple[int, ...] = (7, 30),
) -> dict[str, Any]:
    by_target = _dedupe_latest_per_day(stream_rows)
    targets_out: list[dict[str, Any]] = []
    watchlist: list[dict[str, Any]] = []
    early_watchlist: list[dict[str, Any]] = []

    for tid in sorted(by_target.keys()):
        days_map = by_target[tid]
        series: list[dict[str, Any]] = []
        numeric: list[tuple[str, float]] = []
        for day in sorted(days_map.keys()):
            r = days_map[day]
            h = _hit(r)
            entry = {
                "day": day,
                "hit_rate": h,
                "n_evaluated": (r.get("metrics") or {}).get("n_evaluated"),
                "alert_1_pass": (r.get("metrics") or {}).get("alert_1_pass"),
                "generated_at_utc": r.get("generated_at_utc"),
            }
            series.append(entry)
            if h is not None:
                numeric.append((day, h))

        rolling: dict[str, Any] = {}
        for w in rolling_windows:
            tail = [h for _, h in numeric[-w:]]
            rolling[f"mean_hit_last_{w}d"] = round(sum(tail) / len(tail), 6) if tail else None
            rolling[f"n_days_last_{w}d"] = len(tail)

        streak = _consecutive_pass_streak(numeric, threshold=watchlist_hit_threshold)
        last_hit = numeric[-1][1] if numeric else None
        candidate = (
            streak >= watchlist_streak_days
            and last_hit is not None
            and last_hit >= watchlist_hit_threshold
        )
        early_candidate = (
            len(numeric) >= 2
            and streak >= 2
            and last_hit is not None
            and last_hit >= watchlist_hit_threshold
            and not candidate
        )
        item = {
            "target_id": tid,
            "asset": days_map[sorted(days_map.keys())[-1]].get("asset") if days_map else None,
            "lens_profile": days_map[sorted(days_map.keys())[-1]].get("lens_profile") if days_map else None,
            "n_calendar_days": len(series),
            "last_hit_rate": last_hit,
            "consecutive_days_at_or_above_threshold": streak,
            "watchlist_hit_threshold": watchlist_hit_threshold,
            "watchlist_candidate": candidate,
            "early_watchlist_candidate": early_candidate,
            "rolling": rolling,
            "daily_series": series[-min(14, len(series)) :],
        }
        targets_out.append(item)
        if candidate:
            watchlist.append(
                {
                    "target_id": tid,
                    "last_hit_rate": last_hit,
                    "streak_days": streak,
                    "mean_hit_last_7d": rolling.get("mean_hit_last_7d"),
                    "note_ko": "연구 관측만 — Track A/실매매 자동 승격 아님.",
                }
            )
        elif early_candidate:
            early_watchlist.append(
                {
                    "target_id": tid,
                    "last_hit_rate": last_hit,
                    "streak_days": streak,
                    "mean_hit_last_7d": rolling.get("mean_hit_last_7d"),
                    "note_ko": "초기 2연속일 관측(본 watchlist 3일 미만).",
                }
            )

    watchlist.sort(key=lambda x: (-(x.get("streak_days") or 0), str(x.get("target_id") or "")))
    early_watchlist.sort(key=lambda x: (-(x.get("streak_days") or 0), str(x.get("target_id") or "")))

    return {
        "schema": "sandbox_prophecy_stream_rollup_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "watchlist_policy": {
            "hit_threshold": watchlist_hit_threshold,
            "min_consecutive_days": watchlist_streak_days,
            "track_a_auto_promotion": False,
        },
        "n_stream_rows_read": len(stream_rows),
        "n_targets": len(targets_out),
        "n_watchlist_candidates": len(watchlist),
        "n_early_watchlist_candidates": len(early_watchlist),
        "targets": targets_out,
        "watchlist": watchlist,
        "early_watchlist": early_watchlist,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stream-jsonl", type=Path, default=DEFAULT_STREAM)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--watchlist-json", type=Path, default=DEFAULT_WATCHLIST)
    ap.add_argument("--watchlist-hit-threshold", type=float, default=0.55)
    ap.add_argument("--watchlist-streak-days", type=int, default=3)
    args = ap.parse_args()

    if not args.stream_jsonl.is_file():
        print(f"Missing stream: {args.stream_jsonl}", file=__import__("sys").stderr)
        return 2

    rollup = build_rollup(
        _read_jsonl(args.stream_jsonl),
        watchlist_hit_threshold=args.watchlist_hit_threshold,
        watchlist_streak_days=args.watchlist_streak_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rollup, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    wl_doc = {
        "schema": "sandbox_prophecy_watchlist_v1",
        "generated_at_utc": rollup["generated_at_utc"],
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "policy": rollup["watchlist_policy"],
        "candidates": rollup["watchlist"],
        "early_candidates": rollup.get("early_watchlist") or [],
    }
    args.watchlist_json.write_text(json.dumps(wl_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.output.resolve()}")
    print(f"WROTE: {args.watchlist_json.resolve()}")
    print(f"targets={rollup['n_targets']} watchlist={rollup['n_watchlist_candidates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
