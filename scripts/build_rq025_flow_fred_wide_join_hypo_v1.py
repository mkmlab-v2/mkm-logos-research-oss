#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025: dual-cohort flow + FRED wide join (alignment expansion)."""
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

DEFAULT_FLOW_JOIN = ROOT / "reports/rq024_a_flow_eval_date_join_poc_v1_latest.json"
DEFAULT_FRED_JOIN = ROOT / "reports/btrack_session_panel_fred_lambda_join_252d_hypo_v1_latest.json"
DEFAULT_HYBRID_SCORE = ROOT / "reports/btrack_prophecy_score_hybrid_session_kospi_252d_v1.json"
DEFAULT_DAILY_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/rq025_flow_fred_wide_join_hypo_v1_latest.json"
DEFAULT_MACRO_CSV = Path("G:/공유 드라이브/MKM_DATA_VAULT/data/macro_alerts/sgp_history_master_real.csv")
SCHEMA = "rq025_flow_fred_wide_join_hypo_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_macro_csv(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("") or row.get("date") or "").strip()[:10]
            if len(dk) != 10 and row:
                dk = str(next(iter(row.values())) or "")[:10]
            if len(dk) != 10:
                continue
            entry: dict[str, Any] = {"date": dk}
            for col in ("S", "L", "K", "M", "lambda_t", "gradient", "alert_level", "z_score"):
                raw = row.get(col)
                if raw is None or str(raw).strip() == "":
                    continue
                try:
                    entry[col] = float(raw)
                except (TypeError, ValueError):
                    entry[col] = str(raw).strip()
            out[dk] = entry
    return out


def _fred_by_date_with_ffill(
    macro_map: dict[str, dict[str, Any]],
    dates_needed: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Forward-fill macro after last observed row — [HYPO] observation only."""
    if not macro_map:
        return {}, {"ffill_applied": False, "macro_max_date": None, "n_ffill_dates": 0}
    max_obs = max(macro_map)
    last_row = macro_map[max_obs]
    out = dict(macro_map)
    n_ffill = 0
    for dk in sorted(dates_needed):
        if dk in out:
            continue
        if dk > max_obs:
            ff = dict(last_row)
            ff["macro_ffill"] = True
            ff["macro_ffill_from"] = max_obs
            out[dk] = ff
            n_ffill += 1
    meta = {
        "ffill_applied": n_ffill > 0,
        "macro_max_date": max_obs,
        "n_ffill_dates": n_ffill,
        "boundary_ack": "ffill is HYPO join-rate probe only; not live regime trigger",
    }
    return out, meta


def _fred_by_date(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    doc = _load_json(path)
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("rows") or []:
        dk = str(row.get("session_local_date") or "")[:10]
        if len(dk) != 10:
            continue
        if row.get("macro_present") and isinstance(row.get("macro"), dict):
            out[dk] = row["macro"]
    return out


def _daily_flow_by_date(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            if len(dk) != 10:
                continue
            entry: dict[str, Any] = {"date": dk}
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
            out[dk] = entry
    return out


def _cohort_flow_panel(
    flow_doc: dict[str, Any],
    fred_by_date: dict[str, dict[str, Any]],
    daily_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    for row in flow_doc.get("rows") or []:
        dk = str(row.get("eval_date") or "")[:10]
        if len(dk) != 10:
            continue
        daily = row.get("daily_flow") if row.get("daily_flow_present") else daily_by_date.get(dk)
        macro = fred_by_date.get(dk)
        rows_out.append(
            {
                "eval_date": dk,
                "cohort": "flow_panel_30d",
                "panel_hit": row.get("panel_hit"),
                "predicted_direction": row.get("predicted_direction"),
                "actual_direction": row.get("actual_direction"),
                "flow_score_monthly_rollup": row.get("flow_score_monthly_rollup"),
                "flow_score_single_day_proxy": row.get("flow_score_single_day_proxy"),
                "foreign_flow_sign": row.get("foreign_flow_sign"),
                "daily_flow_present": bool(daily),
                "daily_flow": daily,
                "macro_present": macro is not None,
                "macro": macro,
            }
        )
    return rows_out


def _cohort_hybrid_252d(
    score_doc: dict[str, Any],
    fred_by_date: dict[str, dict[str, Any]],
    daily_by_date: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    for row in score_doc.get("rows") or []:
        if str(row.get("instrument") or "").strip().lower() != "kospi":
            continue
        dk = str(row.get("eval_date") or "")[:10]
        if len(dk) != 10:
            continue
        daily = daily_by_date.get(dk)
        macro = fred_by_date.get(dk)
        pred = str(row.get("predicted_direction") or "").strip().lower()
        actual = str(row.get("actual_direction") or "").strip().lower()
        valid = {"bull", "bear", "neutral"}
        panel_hit = pred == actual if pred in valid and actual in valid else None
        rows_out.append(
            {
                "eval_date": dk,
                "cohort": "hybrid_kospi_252d",
                "panel_hit": panel_hit,
                "predicted_direction": row.get("predicted_direction"),
                "actual_direction": row.get("actual_direction"),
                "daily_flow_present": daily is not None,
                "daily_flow": daily,
                "macro_present": macro is not None,
                "macro": macro,
            }
        )
    return rows_out


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n_rows": 0, "macro_join_rate": 0.0, "daily_flow_join_rate": 0.0}
    n_macro = sum(1 for r in rows if r.get("macro_present"))
    n_flow = sum(1 for r in rows if r.get("daily_flow_present"))
    dates = [str(r.get("eval_date")) for r in rows if r.get("eval_date")]
    return {
        "n_rows": n,
        "macro_join_rate": round(n_macro / n, 6),
        "daily_flow_join_rate": round(n_flow / n, 6),
        "n_macro_joined": n_macro,
        "n_daily_flow_joined": n_flow,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--flow-join-json", type=Path, default=DEFAULT_FLOW_JOIN)
    ap.add_argument("--fred-join-json", type=Path, default=DEFAULT_FRED_JOIN)
    ap.add_argument("--hybrid-score-json", type=Path, default=DEFAULT_HYBRID_SCORE)
    ap.add_argument("--daily-flow-csv", type=Path, default=DEFAULT_DAILY_FLOW)
    ap.add_argument("--macro-csv", type=Path, default=DEFAULT_MACRO_CSV)
    ap.add_argument(
        "--macro-source",
        choices=("fred_join", "vault_csv", "fred_then_vault"),
        default="fred_join",
        help="fred_join=session panel JSON; vault_csv=Vault CSV only; fred_then_vault=FRED then Vault fill",
    )
    ap.add_argument(
        "--macro-ffill",
        action="store_true",
        help="Forward-fill macro after Vault CSV max date for flow-panel dates [HYPO]",
    )
    ap.add_argument(
        "--macro-csv-overlay",
        action="store_true",
        help="Overlay --macro-csv rows onto fred_by_date (local merged extension)",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    flow_path = args.flow_join_json if args.flow_join_json.is_absolute() else ROOT / args.flow_join_json
    fred_path = args.fred_join_json if args.fred_join_json.is_absolute() else ROOT / args.fred_join_json
    hybrid_path = args.hybrid_score_json if args.hybrid_score_json.is_absolute() else ROOT / args.hybrid_score_json
    daily_path = args.daily_flow_csv if args.daily_flow_csv.is_absolute() else ROOT / args.daily_flow_csv
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    if not flow_path.is_file():
        raise SystemExit(f"missing flow join: {flow_path}")
    if not hybrid_path.is_file():
        raise SystemExit(f"missing hybrid score: {hybrid_path}")

    macro_csv_path = args.macro_csv
    macro_csv_map = _load_macro_csv(macro_csv_path) if macro_csv_path.is_file() else {}
    fred_join_map = _fred_by_date(fred_path) if fred_path.is_file() else {}
    if args.macro_source == "vault_csv":
        fred_by_date = dict(macro_csv_map)
    elif args.macro_source == "fred_then_vault":
        fred_by_date = dict(fred_join_map)
        for dk, macro in macro_csv_map.items():
            if dk not in fred_by_date:
                fred_by_date[dk] = macro
    else:
        fred_by_date = dict(fred_join_map)
    macro_freshness = {
        "macro_source": args.macro_source,
        "macro_csv": str(macro_csv_path),
        "macro_csv_present": macro_csv_path.is_file(),
        "macro_csv_max_date": max(macro_csv_map) if macro_csv_map else None,
        "fred_join_max_date": max(fred_join_map) if fred_join_map else None,
    }
    ffill_meta: dict[str, Any] = {"ffill_applied": False}
    overlay_meta: dict[str, Any] = {"overlay_applied": False, "n_overlay_dates": 0}
    if args.macro_csv_overlay and macro_csv_map:
        for dk, macro in macro_csv_map.items():
            fred_by_date[dk] = macro
        overlay_meta = {
            "overlay_applied": True,
            "n_overlay_dates": len(macro_csv_map),
            "overlay_max_date": max(macro_csv_map),
            "boundary_ack": "csv overlay is HYPO; Vault file not mutated",
        }
    if args.macro_ffill and macro_csv_map:
        flow_doc = _load_json(flow_path)
        need_dates = {
            str(r.get("eval_date") or "")[:10]
            for r in flow_doc.get("rows") or []
            if isinstance(r, dict)
        }
        need_dates = {d for d in need_dates if len(d) == 10}
        merged_macro, ffill_meta = _fred_by_date_with_ffill(macro_csv_map, need_dates)
        for dk, macro in merged_macro.items():
            if dk not in fred_by_date or fred_by_date[dk].get("macro_ffill"):
                fred_by_date[dk] = macro
    daily_by_date = _daily_flow_by_date(daily_path)
    flow_rows = _cohort_flow_panel(_load_json(flow_path), fred_by_date, daily_by_date)
    hybrid_rows = _cohort_hybrid_252d(_load_json(hybrid_path), fred_by_date, daily_by_date)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gating": "[NON_GATING]",
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "inputs": {
            "flow_join_json": str(flow_path.relative_to(ROOT)).replace("\\", "/"),
            "fred_join_json": str(fred_path.relative_to(ROOT)).replace("\\", "/") if fred_path.is_file() else None,
            "hybrid_score_json": str(hybrid_path.relative_to(ROOT)).replace("\\", "/"),
            "daily_flow_csv": str(daily_path.relative_to(ROOT)).replace("\\", "/"),
            "fred_macro_max_date": max(fred_by_date) if fred_by_date else None,
            "macro_freshness": macro_freshness,
            "macro_ffill": ffill_meta,
            "macro_csv_overlay": overlay_meta,
        },
        "cohorts": {
            "flow_panel_30d": _summarize(flow_rows),
            "hybrid_kospi_252d": _summarize(hybrid_rows),
        },
        "rows_flow_panel_30d": flow_rows,
        "rows_hybrid_kospi_252d": hybrid_rows,
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fp = payload["cohorts"]["flow_panel_30d"]
    hy = payload["cohorts"]["hybrid_kospi_252d"]
    print(
        f"WROTE: {out_path} flow_macro={fp['macro_join_rate']} "
        f"hybrid_macro={hy['macro_join_rate']} hybrid_flow={hy['daily_flow_join_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
