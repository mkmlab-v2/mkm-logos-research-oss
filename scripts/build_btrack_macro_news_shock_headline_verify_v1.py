#!/usr/bin/env python3
"""Build macro_news_shock headline NLP verify board from pre_news_shadow_input [HYPO]."""

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

from scripts.btrack_macro_news_shock_headline_verify_lib_v1 import (  # noqa: E402
    _read_json,
    build_headline_verify_board,
    load_merged_pre_news_doc,
)

DEFAULT_PRE_NEWS = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
DEFAULT_CAL = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_macro_news_shock_headline_verify_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/btrack_macro_news_shock_headline_verify_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre-news", type=Path, default=DEFAULT_PRE_NEWS)
    ap.add_argument("--calendar", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--min-macro-hits", type=int, default=1)
    ap.add_argument("--min-bear-hits", type=int, default=1)
    ap.add_argument("--shock-score-threshold", type=float, default=0.35)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    args = ap.parse_args()

    pre = load_merged_pre_news_doc(latest_path=args.pre_news if args.pre_news.is_absolute() else ROOT / args.pre_news)
    cal = _read_json(args.calendar if args.calendar.is_absolute() else ROOT / args.calendar)
    dates = [str(d) for d in (cal.get("trading_days") or []) if d]

    doc = build_headline_verify_board(
        pre,
        dates,
        min_macro_hits=args.min_macro_hits,
        min_bear_hits=args.min_bear_hits,
        shock_score_threshold=args.shock_score_threshold,
    )
    doc.update(
        {
            "generated_at_utc": _utc(),
            "research_only": True,
            "send_gate": "HOLD",
            "pre_news_path": str(args.pre_news),
            "year_month": cal.get("year_month"),
        }
    )

    for p in (args.output, args.artifact):
        p = p if p.is_absolute() else ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "n_headline_scorable": doc["n_headline_scorable"],
                "n_headline_shock_days": doc["n_headline_shock_days"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
