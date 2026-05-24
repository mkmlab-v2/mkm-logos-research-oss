#!/usr/bin/env python3
"""Morning NASDAQ settlement (~07:50 KST) — score prior session vs yesterday sealed briefing [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
KST = ZoneInfo("Asia/Seoul")
BRIEFING_LOG = ROOT / "reports" / "briefing_log"
DEFAULT_OUT = ROOT / "reports" / "commander_morning_nasdaq_settlement_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def settle_nasdaq(archive_path: Path) -> Dict[str, Any]:
    from scripts.multi_asset_market_adapter_v1 import NASDAQ_CSV, _daily_return  # noqa: WPS433
    from scripts.score_commander_evening_briefing_v1 import _score_prediction  # noqa: WPS433

    env = _read_json(archive_path)
    briefing = env.get("briefing") or env
    cal = str(env.get("calendar_kst") or briefing.get("calendar_kst") or "")

    rows_path = NASDAQ_CSV
    if not rows_path.is_file():
        return {
            "schema": "commander_morning_nasdaq_settlement_v1",
            "calendar_kst": cal,
            "error": "nasdaq_csv_missing",
            "archive_path": str(archive_path),
        }

    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: WPS433

    rows = load_kospi_yf_rows(rows_path)
    if len(rows) < 2:
        return {"schema": "commander_morning_nasdaq_settlement_v1", "calendar_kst": cal, "error": "insufficient_rows"}

    last_date = str(rows[-1].get("date") or "")[:10]
    ret, mdir = _daily_return(rows_path, last_date)

    scored: List[Dict[str, Any]] = []
    for pred in briefing.get("predictions") or []:
        if not isinstance(pred, dict):
            continue
        against = [str(x) for x in (pred.get("score_against") or [])]
        if not any("nasdaq" in a for a in against):
            continue
        s = _score_prediction(pred, market_direction=mdir)
        s["asset"] = "nasdaq"
        s["session_date"] = last_date
        scored.append(s)

    return {
        "schema": "commander_morning_nasdaq_settlement_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "settled_at_utc": _utc_now(),
        "calendar_kst": cal,
        "briefing_id": briefing.get("briefing_id"),
        "archive_path": str(archive_path),
        "nasdaq_session_date": last_date,
        "market_direction": mdir,
        "market_return_pct": round(ret * 100, 4) if ret is not None else None,
        "prediction_scores": scored,
        "n_scored": len(scored),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-kst", default="", help="Settlement run date (default today KST)")
    ap.add_argument(
        "--archive-date-kst",
        default="",
        help="Morning archive date (default: yesterday KST)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    today = args.date_kst or datetime.now(KST).strftime("%Y-%m-%d")
    if args.archive_date_kst:
        arch_date = args.archive_date_kst
    else:
        d = datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=KST) - timedelta(days=1)
        arch_date = d.strftime("%Y-%m-%d")

    path = BRIEFING_LOG / f"{arch_date}_morning_briefing_v1.json"
    if not path.is_file():
        raise SystemExit(f"missing archive: {path}")

    doc = settle_nasdaq(path)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log_path = BRIEFING_LOG / f"{today}_morning_nasdaq_settlement_v1.json"
    log_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json} n_scored={doc.get('n_scored')} dir={doc.get('market_direction')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
