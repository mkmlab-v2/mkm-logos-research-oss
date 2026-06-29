#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured miss-day insight from calendar + eval + 4AI overlay [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CAL = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_FOUR_AI = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_daily_miss_insight_v1_latest.json"
SCHEMA = "kospi_june2026_daily_miss_insight_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _row_by_date(rows: list[dict[str, Any]], session_date: str) -> dict[str, Any] | None:
    for r in rows:
        if str(r.get("session_date") or "") == session_date:
            return r
    return None


def _suppressed_bear_channels(blend: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ch in blend.get("channels") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("direction") or "") != "bear":
            continue
        w = float(ch.get("weight") or 0.0)
        if w <= 0.0:
            out.append(
                {
                    "channel": ch.get("channel"),
                    "direction": ch.get("direction"),
                    "weight": w,
                    "meta": ch.get("meta"),
                }
            )
    return out


def build_daily_miss_insight(
    *,
    session_date: str,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    four_ai: dict[str, Any],
) -> dict[str, Any] | None:
    eval_row = _row_by_date(list(eval_doc.get("rows") or []), session_date)
    if not eval_row:
        return None

    outcome = str(eval_row.get("outcome") or "")
    if outcome not in ("FAIL", "NEUTRAL_DRAW"):
        return None

    cal_row = _row_by_date(list(calendar.get("rows") or []), session_date) or {}
    ai_row = _row_by_date(list(four_ai.get("rows") or []), session_date) or {}
    blend = cal_row.get("blend") if isinstance(cal_row.get("blend"), dict) else {}
    ab = ai_row.get("absolute_balance") if isinstance(ai_row.get("absolute_balance"), dict) else {}
    prophecy = cal_row.get("kospi_index_prophecy") if isinstance(cal_row.get("kospi_index_prophecy"), dict) else {}

    suppressed = _suppressed_bear_channels(blend)
    paradox = outcome == "FAIL" and eval_row.get("band_hit") is True

    lessons: list[str] = []
    if suppressed:
        lessons.append(
            f"bear channels present but zero-weight: {', '.join(str(c.get('channel')) for c in suppressed)}"
        )
    if paradox:
        lessons.append("direction FAIL but close band HIT — level vs direction divergence")
    if ab.get("aligned_with_v2_channel") is False:
        lessons.append("4AI coordinator diverged from v2 channel consensus")

    return {
        "schema": SCHEMA,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "generated_at_utc": _utc_now(),
        "session_date": session_date,
        "outcome": outcome,
        "score": {
            "predicted_direction": eval_row.get("predicted_direction"),
            "actual_direction": eval_row.get("actual_direction"),
            "daily_return_pct": eval_row.get("daily_return_pct"),
            "prior_close": eval_row.get("prior_close"),
            "actual_close": eval_row.get("actual_close"),
            "predicted_close_mid": eval_row.get("predicted_close_mid"),
            "band_hit": eval_row.get("band_hit"),
        },
        "multilens": {
            "predicted_direction": cal_row.get("predicted_direction"),
            "blend_profile": blend.get("profile"),
            "winner_resolution": blend.get("winner_resolution"),
            "votes": blend.get("votes"),
            "blended_score": blend.get("blended_score"),
            "suppressed_bear_channels": suppressed,
        },
        "four_ai": {
            "four_ai_direction": ai_row.get("four_ai_direction"),
            "agents": ai_row.get("four_ai_agents"),
            "coordinator": ab,
        },
        "index_prophecy": prophecy,
        "structured_lessons": lessons,
        "llm_reflect_eligible": outcome == "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-date", required=True, help="KST session date YYYY-MM-DD")
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--four-ai-json", type=Path, default=DEFAULT_FOUR_AI)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args(argv)

    cal_path = args.calendar_json if args.calendar_json.is_absolute() else ROOT / args.calendar_json
    eval_path = args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json
    ai_path = args.four_ai_json if args.four_ai_json.is_absolute() else ROOT / args.four_ai_json

    doc = build_daily_miss_insight(
        session_date=args.session_date.strip()[:10],
        calendar=_load(cal_path),
        eval_doc=_load(eval_path),
        four_ai=_load(ai_path),
    )
    if doc is None:
        print(json.dumps({"ok": True, "skipped": True, "reason": "no_miss_or_neutral_draw_row"}))
        return 0

    if not args.stdout_only:
        out = args.output if args.output.is_absolute() else ROOT / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out} outcome={doc['outcome']}")
    else:
        print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
