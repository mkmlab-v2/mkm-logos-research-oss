#!/usr/bin/env python3
"""[HYPO] Join KOSPI prophecy miss days with daily/monthly investor-flow CSVs.

Reads miss decomposition (frozen-hypothesis panel) and attaches flow context for
operator review. Does not mutate score/ensemble artifacts.

flow_score is computed with the same monthly rollup + weights as
build_btrack_prophecy_score_from_ohlcv.py post-processors (bull_reversal etc.),
not the per-date ensemble core.
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

DEFAULT_MISS = ROOT / "reports/kospi_prophecy_miss_decomposition_v1_latest.json"
DEFAULT_DAILY = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_MONTHLY = ROOT / "research/market_data/kospi_monthly_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/kospi_prophecy_miss_flow_probe_v1_latest.json"
SCHEMA = "kospi_prophecy_miss_flow_probe_v1"
DEFAULT_FLOW_WEIGHTS = (0.5, 0.4, 0.1)

FLOW_JOIN_PATH = {
    "ensemble_per_date": {
        "used": False,
        "script": "scripts/btrack_ensemble_per_date_core_v1.py",
        "note": "Per-date lens fusion does not read flow_score or flow CSV.",
    },
    "score_post_process": {
        "used": True,
        "script": "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "flow_csv": "research/market_data/kospi_monthly_flow_external.csv",
        "join_key": "eval_date[:7] -> ym monthly row",
        "field": "flow_score_for_reversal",
        "consumers": [
            "bull_reversal / bear_relax / year_rebound overrides",
            "build_btrack_prophecy_score_insight_sidecar_stub_v1.py",
            "build_btrack_btc_decouple_spike_v2.py (flow_score_for_reversal on KOSPI rows)",
            "build_global_atom_survivor_resonance_daily_v1.py",
        ],
    },
    "observation_only": {
        "script": "scripts/build_kospi_stress_observation_hypothesis_v1.py",
        "note": "Latest monthly foreign_net_buy proxy; not per-date flow_score.",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"missing json: {path}")
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise SystemExit(f"invalid json object: {path}")
    return obj


def _load_daily_flow(path: Path) -> dict[str, dict[str, Any]]:
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
            if row.get("source_note"):
                entry["source_note"] = str(row.get("source_note"))
            out[d] = entry
    return out


def _csv_date_summary(by_date: dict[str, dict[str, Any]], *, ym: str | None = None) -> dict[str, Any]:
    dates = sorted(by_date.keys())
    if ym:
        dates = [d for d in dates if d.startswith(ym)]
    return {
        "row_count": len(dates),
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "dates": dates,
    }


def _monthly_row(flow_ctx: dict[str, dict[str, float]], ym: str) -> dict[str, Any] | None:
    row = flow_ctx.get(ym)
    if not row:
        return None
    return {
        "ym": ym,
        "foreign_net_buy": row.get("foreign_net_buy"),
        "institution_net_buy": row.get("institution_net_buy"),
        "program_net_buy": row.get("program_net_buy"),
    }


def _data_gap_notes(daily: dict[str, dict[str, Any]], flow_ctx: dict[str, dict[str, float]]) -> list[str]:
    notes: list[str] = []
    if not daily:
        notes.append("daily_flow_csv missing or empty; per-date 수급 join unavailable.")
    else:
        may = _csv_date_summary(daily, ym="2026-05")
        if may["row_count"] == 1 and may["date_min"] == "2026-05-29":
            notes.append(
                "May 2026 daily flow has a single row (2026-05-29 only); "
                "do not treat kospi_monthly_flow_external 2026-05 as full-month totals."
            )
        elif may["row_count"] == 0:
            notes.append("May 2026 has no daily flow rows in CSV.")
    if "2026-05" in flow_ctx and daily:
        may_n = _csv_date_summary(daily, ym="2026-05")["row_count"]
        if may_n < 5:
            notes.append(
                f"monthly 2026-05 rollup derived from daily_n={may_n}; "
                "institution/foreign sums are partial-month proxies only."
            )
    return notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--miss-json", type=Path, default=DEFAULT_MISS)
    ap.add_argument("--daily-flow-csv", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--monthly-flow-csv", type=Path, default=DEFAULT_MONTHLY)
    ap.add_argument("--flow-weights", default="0.5,0.4,0.1", help="foreign,institution,program")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    miss_path = args.miss_json if args.miss_json.is_absolute() else ROOT / args.miss_json
    daily_path = args.daily_flow_csv if args.daily_flow_csv.is_absolute() else ROOT / args.daily_flow_csv
    monthly_path = (
        args.monthly_flow_csv if args.monthly_flow_csv.is_absolute() else ROOT / args.monthly_flow_csv
    )
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    miss = _load_json(miss_path)
    miss_days = [m for m in (miss.get("miss_days") or []) if isinstance(m, dict)]
    if not miss_days:
        raise SystemExit(f"no miss_days in {miss_path}")

    wf, wi, wp = [float(x.strip()) for x in str(args.flow_weights).split(",")]
    daily_by_date = _load_daily_flow(daily_path)
    flow_ctx = _load_monthly_flow_context(monthly_path)

    probe_rows: list[dict[str, Any]] = []
    for m in miss_days:
        ed = str(m.get("eval_date") or "")[:10]
        if not ed:
            continue
        ym = ed[:7]
        daily_row = daily_by_date.get(ed)
        monthly_row = _monthly_row(flow_ctx, ym)
        flow_score = _flow_score_for_eval_date(ed, flow_ctx, w_foreign=wf, w_inst=wi, w_prog=wp)
        daily_flow_score = None
        if daily_row:
            daily_flow_score = _flow_score_for_eval_date(
                ed,
                {ym: {
                    "foreign_net_buy": float(daily_row.get("foreign_net_buy") or 0.0),
                    "institution_net_buy": float(daily_row.get("institution_net_buy") or 0.0),
                    "program_net_buy": float(daily_row.get("program_net_buy") or 0.0),
                }},
                w_foreign=wf,
                w_inst=wi,
                w_prog=wp,
            )
        probe_rows.append(
            {
                "eval_date": ed,
                "kospi_pred": m.get("kospi_pred"),
                "kospi_actual": m.get("kospi_actual"),
                "kospi_ret_pct": m.get("kospi_ret_pct"),
                "btc_pred": m.get("btc_pred"),
                "btc_hit": m.get("btc_hit"),
                "tags": m.get("tags") or [],
                "daily_flow": daily_row,
                "daily_flow_present": daily_row is not None,
                "monthly_flow_ym": ym,
                "monthly_flow": monthly_row,
                "flow_score_monthly_rollup": round(flow_score, 6),
                "flow_score_single_day_proxy": round(daily_flow_score, 6) if daily_flow_score is not None else None,
                "bull_reversal_strong_flow_threshold_ref": 6000.0,
                "would_meet_strong_flow_threshold": flow_score >= 6000.0,
            }
        )

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "miss_decomposition_path": _rel(miss_path),
        "daily_flow_path": _rel(daily_path),
        "monthly_flow_path": _rel(monthly_path),
        "flow_score_weights": {"foreign": wf, "institution": wi, "program": wp},
        "flow_join_path": FLOW_JOIN_PATH,
        "data_gaps": _data_gap_notes(daily_by_date, flow_ctx),
        "daily_flow_summary": _csv_date_summary(daily_by_date),
        "monthly_flow_months": sorted(flow_ctx.keys()),
        "miss_days_with_flow": probe_rows,
        "miss_day_count": len(probe_rows),
        "miss_days_with_daily_flow": sum(1 for r in probe_rows if r.get("daily_flow_present")),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} miss_days={len(probe_rows)} daily_hits={doc['miss_days_with_daily_flow']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
