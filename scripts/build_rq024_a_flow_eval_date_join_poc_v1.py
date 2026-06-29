#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-024-A: join KOSPI score rows with daily investor flow by eval_date.

PoC for per-date flow attachment on the active prophecy panel (not miss-only).
Does not mutate production score JSON or merge into lens promotion.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _flow_score_for_eval_date,
    _load_monthly_flow_context,
)

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DAILY = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_MONTHLY = ROOT / "research/market_data/kospi_monthly_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/rq024_a_flow_eval_date_join_poc_v1_latest.json"
SCHEMA = "rq024_a_flow_eval_date_join_poc_v1"
VALID = {"bull", "bear", "neutral"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_daily(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = str(row.get("date") or "")[:10]
            if len(d) != 10:
                continue
            entry: dict[str, Any] = {"date": d}
            for col in (
                "foreign_net_buy",
                "institution_net_buy",
                "program_net_buy",
                "individual_net_buy",
            ):
                raw = row.get(col)
                if raw is None or str(raw).strip() == "":
                    continue
                try:
                    entry[col] = float(raw)
                except (TypeError, ValueError):
                    entry[col] = raw
            out[d] = entry
    return out


def _hit(pred: str, actual: str) -> bool | None:
    p, a = pred.strip().lower(), actual.strip().lower()
    if p not in VALID or a not in VALID:
        return None
    return p == a


def _foreign_sign(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    try:
        v = float(row.get("foreign_net_buy") or 0.0)
    except (TypeError, ValueError):
        return None
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--daily-flow-csv", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--monthly-flow-csv", type=Path, default=DEFAULT_MONTHLY)
    ap.add_argument("--instrument", default="kospi")
    ap.add_argument("--flow-weights", default="0.5,0.4,0.1")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    daily_path = args.daily_flow_csv if args.daily_flow_csv.is_absolute() else ROOT / args.daily_flow_csv
    monthly_path = (
        args.monthly_flow_csv if args.monthly_flow_csv.is_absolute() else ROOT / args.monthly_flow_csv
    )
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    doc = _load_json(score_path)
    inst_want = str(args.instrument).strip().lower()
    rows = [
        r
        for r in doc.get("rows", [])
        if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst_want
    ]
    if not rows:
        raise SystemExit(f"no rows for instrument={inst_want} in {score_path}")

    wf, wi, wp = [float(x.strip()) for x in str(args.flow_weights).split(",")]
    daily = _load_daily(daily_path)
    flow_ctx = _load_monthly_flow_context(monthly_path)

    joined: list[dict[str, Any]] = []
    hits_with_flow = hits_without = 0
    n_with_flow = 0
    foreign_align_hits = foreign_align_n = 0

    for r in rows:
        ed = str(r.get("eval_date") or "")[:10]
        pred = str(r.get("predicted_direction") or "").strip().lower()
        actual = str(r.get("actual_direction") or "").strip().lower()
        daily_row = daily.get(ed)
        ym = ed[:7]
        monthly_score = _flow_score_for_eval_date(ed, flow_ctx, w_foreign=wf, w_inst=wi, w_prog=wp)
        daily_score = None
        if daily_row:
            daily_score = _flow_score_for_eval_date(
                ed,
                {
                    ym: {
                        "foreign_net_buy": float(daily_row.get("foreign_net_buy") or 0.0),
                        "institution_net_buy": float(daily_row.get("institution_net_buy") or 0.0),
                        "program_net_buy": float(daily_row.get("program_net_buy") or 0.0),
                    }
                },
                w_foreign=wf,
                w_inst=wi,
                w_prog=wp,
            )
        h = _hit(pred, actual)
        if daily_row:
            n_with_flow += 1
            if h is True:
                hits_with_flow += 1
            elif h is False:
                hits_without += 1
            fs = _foreign_sign(daily_row)
            if fs in VALID and actual in VALID:
                foreign_align_n += 1
                if fs == actual:
                    foreign_align_hits += 1
        joined.append(
            {
                "eval_date": ed,
                "predicted_direction": pred,
                "actual_direction": actual,
                "panel_hit": h,
                "daily_flow_present": daily_row is not None,
                "daily_flow": daily_row,
                "flow_score_monthly_rollup": round(monthly_score, 6),
                "flow_score_single_day_proxy": round(daily_score, 6) if daily_score is not None else None,
                "foreign_flow_sign": _foreign_sign(daily_row),
            }
        )

    eval_dates = sorted({str(r.get("eval_date") or "")[:10] for r in rows})
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gating": "[NON_GATING]",
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024-A",
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)).replace("\\", "/"),
            "daily_flow_csv": str(daily_path.relative_to(ROOT)).replace("\\", "/"),
            "monthly_flow_csv": str(monthly_path.relative_to(ROOT)).replace("\\", "/"),
            "instrument": inst_want,
            "n_panel_rows": len(rows),
            "n_distinct_eval_dates": len(eval_dates),
            "eval_date_min": eval_dates[0] if eval_dates else None,
            "eval_date_max": eval_dates[-1] if eval_dates else None,
        },
        "join_summary": {
            "daily_flow_join_rate": round(n_with_flow / len(rows), 6) if rows else None,
            "n_with_daily_flow": n_with_flow,
            "n_missing_daily_flow": len(rows) - n_with_flow,
            "panel_hit_rate_where_flow_present": round(hits_with_flow / n_with_flow, 6)
            if n_with_flow
            else None,
            "foreign_sign_matches_actual_rate": round(foreign_align_hits / foreign_align_n, 6)
            if foreign_align_n
            else None,
            "foreign_sign_n": foreign_align_n,
        },
        "rows": joined,
        "boundary_ack": "Observation-only join PoC; do not merge into BTC lens 0.52 / Track A claims.",
        "track_wall": {"auto_bridge_to_a_track": False, "live_trading_trigger": False},
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} join_rate={out['join_summary']['daily_flow_join_rate']} "
        f"n={len(rows)} with_flow={n_with_flow}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
