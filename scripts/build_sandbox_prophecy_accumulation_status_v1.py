#!/usr/bin/env python3
"""SANDBOX calendar-day accumulation status (watchlist / holdout readiness)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROLLUP = ROOT / "reports/sandbox_prophecy_rollup_v1_latest.json"
DEFAULT_WATCHLIST = ROOT / "reports/sandbox_prophecy_watchlist_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_accumulation_status_v1_latest.json"


def _next_milestone_ko(
    *,
    max_days: int,
    days_until: int,
    watchlist_gate_open: bool,
    holdout_gate_likely_open: bool,
    n_full_watchlist: int,
) -> str:
    if watchlist_gate_open and holdout_gate_likely_open and n_full_watchlist > 0:
        return "full watchlist·holdout 평가 가능 — human_review_pack 휴먼 검토(자동 승격 없음)"
    if watchlist_gate_open:
        return "full watchlist 판정 가능 — holdout pass는 UTC 4일+ 스냅샷 후"
    if days_until == 1:
        return "내일 UTC 일일 체인 1회 후 full watchlist(≥55%, 3일 streak) 판정 가능"
    if days_until > 1:
        return f"UTC 일일 체인 {days_until}일 더 필요(full watchlist 게이트)"
    return "일일 체인 실행 후 accumulation·watchlist 재평가"


def build_status(
    rollup: dict[str, Any] | None,
    watchlist: dict[str, Any] | None,
    *,
    min_streak_days: int = 3,
    hit_threshold: float = 0.55,
) -> dict[str, Any]:
    max_days = 0
    near_watchlist: list[dict[str, Any]] = []
    full_watchlist_ids = {
        str(c.get("target_id"))
        for c in (watchlist or {}).get("candidates") or []
        if isinstance(c, dict) and c.get("target_id")
    }
    early_ids = {
        str(c.get("target_id"))
        for c in (watchlist or {}).get("early_candidates") or []
        if isinstance(c, dict) and c.get("target_id")
    }

    for t in (rollup or {}).get("targets") or []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("target_id") or "")
        n_days = int(t.get("n_calendar_days") or 0)
        max_days = max(max_days, n_days)
        streak = int(t.get("consecutive_days_at_or_above_threshold") or 0)
        if tid in full_watchlist_ids:
            lane = "full_watchlist"
        elif tid in early_ids:
            lane = "early_watchlist"
        elif streak >= 1 and streak < min_streak_days:
            near_watchlist.append(
                {
                    "target_id": tid,
                    "streak_days": streak,
                    "days_until_full_watchlist": max(0, min_streak_days - streak),
                    "last_hit_rate": t.get("last_hit_rate"),
                    "mean_hit_last_7d": t.get("mean_hit_last_7d"),
                }
            )
        elif n_days < min_streak_days:
            near_watchlist.append(
                {
                    "target_id": tid,
                    "streak_days": streak,
                    "days_until_full_watchlist": max(0, min_streak_days - max(streak, n_days)),
                    "last_hit_rate": t.get("last_hit_rate"),
                    "reason": "insufficient_calendar_days",
                }
            )

    near_watchlist.sort(
        key=lambda x: (-(x.get("streak_days") or 0), str(x.get("target_id") or ""))
    )

    days_until = max(0, min_streak_days - max_days)
    gate_open = max_days >= min_streak_days
    holdout_open = max_days >= 4

    return {
        "schema": "sandbox_prophecy_accumulation_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "policy": {
            "hit_threshold": hit_threshold,
            "min_consecutive_days": min_streak_days,
            "holdout_min_snapshot_days_hint": 4,
        },
        "max_n_calendar_days": max_days,
        "days_until_watchlist_eligible": days_until,
        "watchlist_gate_open": gate_open,
        "holdout_gate_likely_open": holdout_open,
        "next_milestone_ko": _next_milestone_ko(
            max_days=max_days,
            days_until=days_until,
            watchlist_gate_open=gate_open,
            holdout_gate_likely_open=holdout_open,
            n_full_watchlist=len(full_watchlist_ids),
        ),
        "n_full_watchlist": len(full_watchlist_ids),
        "n_early_watchlist": len(early_ids),
        "near_watchlist": near_watchlist[:15],
        "note_ko": (
            "달력 스냅샷일은 일일 체인 실행일 수(UTC) 기준. 동일일 다회 실행은 1일로 dedupe."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rollup-json", type=Path, default=DEFAULT_ROLLUP)
    ap.add_argument("--watchlist-json", type=Path, default=DEFAULT_WATCHLIST)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rollup = None
    if args.rollup_json.is_file():
        rollup = json.loads(args.rollup_json.read_text(encoding="utf-8-sig"))
    watchlist = None
    if args.watchlist_json.is_file():
        watchlist = json.loads(args.watchlist_json.read_text(encoding="utf-8-sig"))

    doc = build_status(rollup, watchlist)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"max_days={doc['max_n_calendar_days']} "
        f"days_until_watchlist={doc['days_until_watchlist_eligible']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
