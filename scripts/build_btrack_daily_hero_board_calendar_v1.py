#!/usr/bin/env python3
"""Build monthly daily hero board calendar (5 slots × trading days) [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_daily_hero_board_lib_v1 import load_context, predict_slot, slot_ids, utc_now  # noqa: E402

DEFAULT_OUT = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/btrack_daily_hero_board_calendar_v1_latest.json"


def _parse_ym(ym: str) -> tuple[str, date, date]:
    y, m = [int(x) for x in ym.split("-")]
    start = date(y, m, 1)
    end = date(y, 12, 31) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)
    return f"{y:04d}-{m:02d}", start, end


def build_calendar(*, year_month: str, seal_date: str | None) -> dict[str, Any]:
    from scripts.kospi_krx_calendar_v1 import krx_trading_days

    ym, d0, d1 = _parse_ym(year_month)
    trading_days = krx_trading_days(d0, d1)
    ctx = load_context()
    rows: list[dict[str, Any]] = []
    for dk in trading_days:
        slot_preds: dict[str, Any] = {}
        for sid in slot_ids():
            slot_preds[sid] = predict_slot(sid, dk, ctx)
        status = "sealed_today" if seal_date and dk == seal_date else ("pending" if dk > (seal_date or dk) else "published")
        rows.append({"session_date": dk, "status": status, "slots": slot_preds})

    return {
        "schema": "btrack_daily_hero_board_calendar_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "year_month": ym,
        "trading_days": trading_days,
        "n_trading_days": len(trading_days),
        "config_path": "data/commander/btrack_daily_hero_board_v1.json",
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default=datetime.now(timezone.utc).strftime("%Y-%m"))
    ap.add_argument("--seal-date", default=None, help="KST YYYY-MM-DD mark sealed_today")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    args = ap.parse_args()

    doc = build_calendar(year_month=args.year_month, seal_date=args.seal_date)
    for p in (args.output, args.artifact):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "n_days": doc["n_trading_days"], "out": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
