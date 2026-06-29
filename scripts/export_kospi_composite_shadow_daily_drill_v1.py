#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export daily composite_bear_conditional shadow drill CSV [HYPO][research_only]."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_daily_hero_board_lib_v1 import predict_slot  # noqa: E402
from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import _coord_raw_bull  # noqa: E402
from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily,
    max_lag_from_rules,
    resolve_prior_foreign_for_gate,
    summarize_flow_gate_usage,
)
from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import (  # noqa: E402
    _paths_for_month,
    build_calendar,
)
from scripts.build_kospi_june2026_neutral_research_bundle_v1 import _resolve_calendar_path  # noqa: E402
from scripts.build_kospi_june2026_parallel_shadow_bundle_v1 import (  # noqa: E402
    BEAR_SCENARIO,
    FOREIGN_SELL_THRESHOLD,
)
from scripts.kospi_composite_shadow_lib_v1 import composite_bear_conditional as composite_direction  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_weight_counterfactual_lib_v1 import replay_scenario  # noqa: E402

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
FLOW_CSV = ROOT / "research/market_data/kospi_daily_flow_external.csv"

CSV_FIELDS = [
    "session_date",
    "year_month",
    "weekday_ko",
    "month_ganji",
    "day_ganji",
    "active",
    "bear_triple",
    "composite",
    "coord_raw",
    "coord_mode",
    "unlock_candidate",
    "allow_unlock",
    "blocks",
    "reason",
    "shock_pred",
    "prior_foreign_net_buy",
    "prior_foreign_source_date",
    "prior_foreign_lag_days",
    "flow_gate_mode",
    "active_bull_votes",
    "active_bear_votes",
    "bear_triple_winner",
    "actual_direction",
    "daily_return_pct",
    "active_outcome",
    "composite_outcome",
    "composite_rescues_active_fail",
    "data_mode",
]


def _utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _month_range(from_ym: str, to_ym: str) -> list[str]:
    y0, m0 = map(int, from_ym.split("-"))
    y1, m1 = map(int, to_ym.split("-"))
    out: list[str] = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _load_calendar(ym: str, *, rebuild: bool) -> dict[str, Any]:
    path, _ = _paths_for_month(ym)
    if path.is_file() and not rebuild:
        return _read(path)
    return build_calendar(year_month=ym, skip_panel=True, profile="v2_multilens")


def _load_eval_by_date(ym: str) -> dict[str, dict[str, Any]]:
    tag = ym.replace("-", "")
    eval_path = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    doc = _read(eval_path)
    return {str(r.get("session_date")): r for r in (doc.get("rows") or []) if r.get("session_date")}


def _classify_reason(
    *,
    active: str,
    bear_triple: str,
    composite: str,
    unlock_candidate: bool,
    allow_unlock: bool,
) -> str:
    if composite == active:
        return "active_unchanged"
    if unlock_candidate and allow_unlock:
        return "4ai_unlock"
    if composite == bear_triple:
        if unlock_candidate and not allow_unlock:
            return "bear_triple_blocked_unlock"
        return "bear_triple_default"
    return "other"


def _data_mode(session_date: str, last_real: str | None) -> str:
    if not last_real:
        return "calendar_blend"
    if session_date > last_real:
        return "forward_sim"
    if session_date <= last_real:
        return "partial_or_real"
    return "calendar_blend"


def build_drill_rows(
    *,
    year_months: list[str],
    rules: dict[str, Any],
    flow: dict[str, float | None],
    last_real_date: str | None,
    rebuild_calendars: bool,
) -> list[dict[str, Any]]:
    eval_stub: dict[str, Any] = {"rows": []}
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}

    rows_out: list[dict[str, Any]] = []
    for ym in year_months:
        cal = _load_calendar(ym, rebuild=rebuild_calendars)
        eval_by = _load_eval_by_date(ym)
        for cr in cal.get("rows") or []:
            dk = str(cr.get("session_date"))
            active = str(cr.get("predicted_direction") or "neutral")
            bear_triple, bear_detail, _ = replay_scenario(
                cr,
                scenario_id=BEAR_SCENARIO,
                neutral_band=neutral_band,
                blend_policy=blend_policy,
            )
            coord_raw, coord_mode = _coord_raw_bull(cr, rules, eval_stub)
            prior_ctx = resolve_prior_foreign_for_gate(
                flow, dk, max_lag_calendar_days=max_lag_from_rules(rules)
            )
            prior_fn = prior_ctx.value
            shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
            allow_unlock, blocks = evaluate_conditional_unlock(
                prior_foreign=prior_fn,
                shock_pred=shock_pred,
                foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
                apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
            )
            block_str = ";".join(blocks)
            if prior_ctx.gate_mode == "skipped_stale_forward":
                block_str = ";".join([b for b in (block_str, "flow_gate_skipped_stale_forward") if b])
            unlock_candidate = active == "neutral" and coord_raw == "bull"
            composite = composite_direction(
                v2=active,
                bear_triple=bear_triple,
                coord_raw=coord_raw,
                unlock_candidate=unlock_candidate,
                cond_allow=allow_unlock,
            )
            reason = _classify_reason(
                active=active,
                bear_triple=bear_triple,
                composite=composite,
                unlock_candidate=unlock_candidate,
                allow_unlock=allow_unlock,
            )
            pillars = cr.get("pillars_session") if isinstance(cr.get("pillars_session"), dict) else {}
            blend = cr.get("blend") if isinstance(cr.get("blend"), dict) else {}
            votes = blend.get("votes") if isinstance(blend.get("votes"), dict) else {}
            ev = eval_by.get(dk) or {}
            actual = str(ev.get("actual_direction") or "") or None
            active_oc = str(ev.get("outcome") or "") or None
            composite_oc = _outcome(composite, actual) if actual else None
            rescue = active_oc == "FAIL" and composite_oc == "HIT" if active_oc and composite_oc else None

            rows_out.append(
                {
                    "session_date": dk,
                    "year_month": ym,
                    "weekday_ko": cr.get("weekday_ko"),
                    "month_ganji": pillars.get("month"),
                    "day_ganji": pillars.get("day"),
                    "active": active,
                    "bear_triple": bear_triple,
                    "composite": composite,
                    "coord_raw": coord_raw,
                    "coord_mode": coord_mode,
                    "unlock_candidate": unlock_candidate,
                    "allow_unlock": allow_unlock,
                    "blocks": block_str,
                    "reason": reason,
                    "shock_pred": shock_pred,
                    "prior_foreign_net_buy": prior_fn,
                    "prior_foreign_source_date": prior_ctx.source_date,
                    "prior_foreign_lag_days": prior_ctx.lag_calendar_days,
                    "flow_gate_mode": prior_ctx.gate_mode,
                    "active_bull_votes": votes.get("bull"),
                    "active_bear_votes": votes.get("bear"),
                    "bear_triple_winner": (bear_detail or {}).get("winner_resolution"),
                    "actual_direction": actual,
                    "daily_return_pct": ev.get("daily_return_pct"),
                    "active_outcome": active_oc,
                    "composite_outcome": composite_oc,
                    "composite_rescues_active_fail": rescue,
                    "data_mode": _data_mode(dk, last_real_date),
                }
            )
    rows_out.sort(key=lambda r: str(r["session_date"]))
    return rows_out


def _last_real_kospi_date() -> str | None:
    import csv as csvmod

    path = ROOT / "research/market_data/kospi_daily_external_yf.csv"
    if not path.is_file():
        return None
    last = None
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csvmod.DictReader(f):
            dk = str(row.get("Date", ""))[:10]
            if len(dk) == 10:
                last = dk
    return last


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [r for r in rows if r.get("actual_direction")]
    return {
        "n_days": len(rows),
        "n_scored": len(scored),
        "composite_direction_counts": dict(Counter(r["composite"] for r in rows)),
        "reason_counts": dict(Counter(r["reason"] for r in rows)),
        "block_counts": dict(
            Counter(b for r in rows for b in ((r.get("blocks") or "").split(";") if r.get("blocks") else ["(none)"]))
        ),
        "composite_rescues_active_fail": sum(1 for r in scored if r.get("composite_rescues_active_fail")),
        "active_directional_hr": (
            round(sum(1 for r in scored if r.get("active_outcome") == "HIT") / max(1, sum(1 for r in scored if r.get("active_outcome") in ("HIT", "FAIL"))), 4)
            if scored
            else None
        ),
        "composite_directional_hr": (
            round(sum(1 for r in scored if r.get("composite_outcome") == "HIT") / max(1, sum(1 for r in scored if r.get("composite_outcome") in ("HIT", "FAIL"))), 4)
            if scored
            else None
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", action="append", dest="year_months", help="YYYY-MM (repeatable)")
    ap.add_argument("--from-month", dest="from_month", help="YYYY-MM range start")
    ap.add_argument("--to-month", dest="to_month", help="YYYY-MM range end")
    ap.add_argument("--output-csv", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument("--rebuild-calendars", action="store_true")
    ns = ap.parse_args()

    months: list[str] = list(ns.year_months or [])
    if ns.from_month and ns.to_month:
        months.extend(_month_range(ns.from_month, ns.to_month))
    if not months:
        ap.error("provide --year-month and/or --from-month --to-month")

    months = sorted(set(months))
    rules = _read(DEFAULT_RULES)
    flow = load_flow_daily(FLOW_CSV)
    last_real = _last_real_kospi_date()
    rows = build_drill_rows(
        year_months=months,
        rules=rules,
        flow=flow,
        last_real_date=last_real,
        rebuild_calendars=ns.rebuild_calendars,
    )
    write_csv(ns.output_csv, rows)
    summary = summarize(rows)
    meta = {
        "schema": "kospi_composite_shadow_daily_drill_export_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "year_months": months,
        "last_real_kospi_date": last_real,
        "flow_csv": str(FLOW_CSV.relative_to(ROOT)).replace("\\", "/"),
        "forward_flow_note_ko": "flow lag>14d → foreign gate skip; stochastic sensitivity = separate arm",
        "csv_path": str(ns.output_csv).replace("\\", "/"),
        **summary,
        **summarize_flow_gate_usage(rows),
        "reproduce": " ".join(
            [
                "py scripts/export_kospi_composite_shadow_daily_drill_v1.py",
                *(f"--year-month {m}" for m in months),
                f"--output-csv {ns.output_csv}",
            ]
        ),
    }
    json_out = ns.output_json or ns.output_csv.with_suffix(".json")
    json_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "csv": str(ns.output_csv), "json": str(json_out), **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
