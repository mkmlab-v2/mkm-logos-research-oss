#!/usr/bin/env python3
"""Score daily hero board calendar vs realized data [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_daily_hero_board_lib_v1 import load_context, score_slot, slot_ids, utc_now  # noqa: E402

KST = ZoneInfo("Asia/Seoul")
DEFAULT_CAL = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_daily_hero_board_eval_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/btrack_daily_hero_board_eval_v1_latest.json"


def _default_as_of() -> str:
    from datetime import date

    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    return last_krx_trading_day_on_or_before(datetime.now(KST).date()) or datetime.now(KST).strftime("%Y-%m-%d")


def eval_board(calendar: dict[str, Any], *, as_of_kst: str) -> dict[str, Any]:
    ctx = load_context()
    row_by = {str(r.get("session_date")): r for r in calendar.get("rows") or []}
    slot_metrics: dict[str, dict[str, Any]] = {
        sid: {"hits": 0, "fails": 0, "neutral": 0, "n_scorable": 0, "brier_sum": 0.0} for sid in slot_ids()
    }
    for sid in slot_ids():
        if sid == "macro_news_shock":
            slot_metrics[sid].update(
                {
                    "proxy_hits": 0,
                    "proxy_fails": 0,
                    "headline_hits": 0,
                    "headline_fails": 0,
                    "n_headline_scorable": 0,
                }
            )
    scored_rows: list[dict[str, Any]] = []

    for dk in calendar.get("trading_days") or []:
        if str(dk) > as_of_kst:
            continue
        prow = row_by.get(str(dk))
        if not prow:
            continue
        slot_scores: dict[str, Any] = {}
        for sid in slot_ids():
            pred = (prow.get("slots") or {}).get(sid) or {}
            sc = score_slot(sid, str(dk), pred, ctx)
            slot_scores[sid] = sc
            if not sc.get("scorable"):
                continue
            m = slot_metrics[sid]
            m["n_scorable"] += 1
            oc = str(sc.get("outcome") or "")
            if oc == "HIT":
                m["hits"] += 1
            elif oc == "FAIL":
                m["fails"] += 1
            else:
                m["neutral"] += 1
            if sc.get("brier_contribution") is not None:
                m["brier_sum"] += float(sc["brier_contribution"])
            if sid == "macro_news_shock" and sc.get("scorable"):
                oc_proxy = str(sc.get("outcome_proxy") or "")
                if oc_proxy == "HIT":
                    m["proxy_hits"] += 1
                elif oc_proxy == "FAIL":
                    m["proxy_fails"] += 1
                if sc.get("headline_scorable"):
                    m["n_headline_scorable"] += 1
                    oc_h = str(sc.get("outcome_headline") or "")
                    if oc_h == "HIT":
                        m["headline_hits"] += 1
                    elif oc_h == "FAIL":
                        m["headline_fails"] += 1
        scored_rows.append({"session_date": dk, "slots": slot_scores})

    for sid, m in slot_metrics.items():
        n = m["n_scorable"]
        n_dir = m["hits"] + m["fails"]
        m["directional_hit_rate"] = round(m["hits"] / n_dir, 4) if n_dir else None
        m["mean_brier"] = round(m["brier_sum"] / n, 6) if n and m["brier_sum"] else None
        if sid == "macro_news_shock":
            n_proxy = int(m.get("proxy_hits", 0)) + int(m.get("proxy_fails", 0))
            m["proxy_directional_hit_rate"] = round(m["proxy_hits"] / n_proxy, 4) if n_proxy else None
            n_h = int(m.get("n_headline_scorable") or 0)
            n_h_dir = int(m.get("headline_hits", 0)) + int(m.get("headline_fails", 0))
            m["headline_directional_hit_rate"] = round(m["headline_hits"] / n_h_dir, 4) if n_h_dir else None
            m["headline_scorable_rate"] = round(n_h / n, 4) if n else None

    return {
        "schema": "btrack_daily_hero_board_eval_v1",
        "generated_at_utc": utc_now(),
        "as_of_kst": as_of_kst,
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "year_month": calendar.get("year_month"),
        "n_session_days": len(scored_rows),
        "slot_metrics": slot_metrics,
        "rows": scored_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    args = ap.parse_args()

    cal_path = args.calendar if args.calendar.is_absolute() else ROOT / args.calendar
    cal = json.loads(cal_path.read_text(encoding="utf-8-sig"))
    doc = eval_board(cal, as_of_kst=args.as_of_kst or _default_as_of())
    for p in (args.output, args.artifact):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output} n_days={doc['n_session_days']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
