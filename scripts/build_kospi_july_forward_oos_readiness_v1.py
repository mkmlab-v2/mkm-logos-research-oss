#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""July forward OOS readiness gate — documents n=0 until first July session scores."""

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

from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before  # noqa: E402

DEFAULT_CAL = ROOT / "reports/kospi_202607_daily_prophecy_calendar_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_202607_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_july_forward_oos_readiness_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_july_forward_oos_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_july_readiness(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    as_of_kst: str,
) -> dict[str, Any]:
    trading_days = [str(d) for d in (calendar.get("trading_days") or [])]
    first_july = trading_days[0] if trading_days else None
    scored = [r for r in (eval_doc.get("rows") or []) if isinstance(r, dict)]
    n_scored = len(scored)
    awaiting = [d for d in trading_days if d > as_of_kst]
    scoreable_now = [d for d in trading_days if d <= as_of_kst]

    status = "accumulating" if n_scored > 0 else "awaiting_first_session"
    if first_july and as_of_kst < first_july:
        status = "pre_month_calendar_only"

    return {
        "schema": "kospi_july_forward_oos_readiness_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "year_month": "2026-07",
        "as_of_kst": as_of_kst,
        "status": status,
        "first_trading_session": first_july,
        "n_calendar_days": len(trading_days),
        "n_scoreable_as_of": len(scoreable_now),
        "n_awaiting_future_session": len(awaiting),
        "n_scored": n_scored,
        "eval_metrics": eval_doc.get("metrics"),
        "next_action_ko": (
            f"첫 July 세션({first_july}) 종료 후 eval_kospi + lane_compare + significance --include-july"
            if status != "accumulating"
            else "July 누적 중 — n>=15 시 gate_reached_bundle 자동 검토"
        ),
        "calendar_path": "reports/kospi_202607_daily_prophecy_calendar_v1.json",
        "eval_path": "reports/kospi_202607_daily_prophecy_eval_latest.json",
        "reproduce": "py scripts/build_kospi_july_forward_oos_readiness_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    ns = ap.parse_args()

    as_of = (ns.as_of_kst or last_krx_trading_day_on_or_before(datetime.now().date()) or "")[:10]
    calendar = _read(ns.calendar_json)
    eval_doc = _read(ns.eval_json)
    doc = build_july_readiness(calendar=calendar, eval_doc=eval_doc, as_of_kst=as_of)

    for p in (ns.out, ns.artifact):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "status": doc["status"], "n_scored": doc["n_scored"], "as_of_kst": as_of}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
