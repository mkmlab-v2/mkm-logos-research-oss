#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append daily channel-level feedback for KOSPI scoring vs composite shadow [HYPO].

Does NOT merge briefing into scoring. Logs per session_date for FAIL learning.
"""

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

from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import _coord_raw_bull  # noqa: E402
from scripts.build_kospi_june2026_parallel_shadow_bundle_v1 import BEAR_SCENARIO  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_composite_shadow_lib_v1 import composite_active_hold, composite_bear_conditional  # noqa: E402
from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily,
    max_lag_from_rules,
    resolve_prior_foreign_for_gate,
)
from scripts.btrack_daily_hero_board_lib_v1 import predict_slot  # noqa: E402
from scripts.kospi_weight_counterfactual_lib_v1 import replay_scenario  # noqa: E402

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_LOG = ROOT / "reports/kospi_daily_channel_feedback_log_v1.jsonl"
FOREIGN_SELL_THRESHOLD = -25000.0


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _calendar_path(year_month: str) -> Path:
    tag = year_month.replace("-", "")
    p = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    if p.is_file():
        return p
    if year_month == "2026-06":
        return ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    return p


def _eval_path(year_month: str) -> Path:
    tag = year_month.replace("-", "")
    return ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"


def _channel_snapshot(cal_row: dict[str, Any]) -> list[dict[str, Any]]:
    blend = cal_row.get("blend") if isinstance(cal_row.get("blend"), dict) else {}
    out: list[dict[str, Any]] = []
    for ch in blend.get("channels") or []:
        if not isinstance(ch, dict):
            continue
        out.append(
            {
                "channel": ch.get("channel"),
                "direction": ch.get("direction"),
                "weight": ch.get("weight"),
            }
        )
    votes = blend.get("votes") if isinstance(blend.get("votes"), dict) else {}
    return out, votes, blend.get("winner"), blend.get("blended_score")


def build_feedback_row(
    *,
    session_date: str,
    year_month: str,
    cal_row: dict[str, Any],
    eval_row: dict[str, Any],
    rules: dict[str, Any],
    flow: dict[str, float | None],
    eval_stub: dict[str, Any],
) -> dict[str, Any]:
    active = str(eval_row.get("predicted_direction") or cal_row.get("predicted_direction") or "neutral")
    actual = str(eval_row.get("actual_direction") or "neutral")
    active_oc = str(eval_row.get("outcome") or _outcome(active, actual))
    nb = float(rules.get("neutral_band", 0.06))
    bp = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    bear_triple, bear_detail, _ = replay_scenario(
        cal_row, scenario_id=BEAR_SCENARIO, neutral_band=nb, blend_policy=bp
    )
    coord_raw, coord_mode = _coord_raw_bull(cal_row, rules, eval_stub)
    prior_ctx = resolve_prior_foreign_for_gate(flow, session_date, max_lag_calendar_days=max_lag_from_rules(rules))
    shock_pred = bool((predict_slot("macro_news_shock", session_date) or {}).get("predicted_binary"))
    allow, blocks = evaluate_conditional_unlock(
        prior_foreign=prior_ctx.value,
        shock_pred=shock_pred,
        foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
        apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
    )
    unlock = active == "neutral" and coord_raw == "bull"
    comp_bear = composite_bear_conditional(
        v2=active, bear_triple=bear_triple, coord_raw=coord_raw,
        unlock_candidate=unlock, cond_allow=allow,
    )
    comp_hold = composite_active_hold(
        v2=active, bear_triple=bear_triple, coord_raw=coord_raw,
        unlock_candidate=unlock, cond_allow=allow,
    )
    channels, votes, winner, blended_score = _channel_snapshot(cal_row)
    suppressed_bear = [c for c in channels if c.get("direction") == "bear" and float(c.get("weight") or 0) == 0]
    comp_bear_oc = _outcome(comp_bear, actual)
    comp_hold_oc = _outcome(comp_hold, actual)
    return {
        "schema": "kospi_daily_channel_feedback_v1",
        "logged_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "session_date": session_date,
        "year_month": year_month,
        "active_direction": active,
        "actual_direction": actual,
        "active_outcome": active_oc,
        "composite_bear_conditional_direction": comp_bear,
        "composite_bear_conditional_outcome": comp_bear_oc,
        "composite_active_hold_direction": comp_hold,
        "composite_active_hold_outcome": comp_hold_oc,
        "composite_rescued_active_fail_bear": active_oc == "FAIL" and comp_bear_oc == "HIT",
        "composite_rescued_active_fail_hold": active_oc == "FAIL" and comp_hold_oc == "HIT",
        "unlock_candidate": unlock,
        "allow_unlock": allow,
        "flow_gate_mode": prior_ctx.gate_mode,
        "blocks": blocks,
        "coordinator_raw": coord_raw,
        "coordinator_mode": coord_mode,
        "bear_triple_direction": bear_triple,
        "blend_winner": winner,
        "blended_score": blended_score,
        "votes": votes,
        "channels": channels,
        "suppressed_bear_channels": suppressed_bear,
        "daily_return_pct": eval_row.get("daily_return_pct"),
        "briefing_merge_forbidden": True,
    }


def append_feedback(
    *,
    year_month: str,
    as_of_kst: str,
    log_path: Path,
    session_date: str | None = None,
) -> dict[str, Any]:
    rules = _read(DEFAULT_RULES)
    flow = load_flow_daily(ROOT / "research/market_data/kospi_daily_flow_external.csv")
    cal = _read(_calendar_path(year_month))
    ev_doc = _read(_eval_path(year_month))
    if year_month == "2026-06" and not ev_doc.get("rows"):
        ev_doc = _read(ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json")
    cal_by = {str(r.get("session_date")): r for r in (cal.get("rows") or [])}
    eval_by = {str(r.get("session_date")): r for r in (ev_doc.get("rows") or []) if str(r.get("session_date")) <= as_of_kst}
    eval_stub: dict[str, Any] = {"rows": list(eval_by.values())}
    targets = [session_date] if session_date else sorted(eval_by.keys())
    appended: list[dict[str, Any]] = []
    existing_dates: set[str] = set()
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing_dates.add(str(json.loads(line).get("session_date")))
            except json.JSONDecodeError:
                continue
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        for dk in targets:
            if dk in existing_dates:
                continue
            ev = eval_by.get(dk)
            cal_row = cal_by.get(dk, {})
            if not ev or not cal_row:
                continue
            row = build_feedback_row(
                session_date=dk,
                year_month=year_month,
                cal_row=cal_row,
                eval_row=ev,
                rules=rules,
                flow=flow,
                eval_stub=eval_stub,
            )
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            appended.append(row)
    fails = sum(1 for r in appended if r.get("active_outcome") == "FAIL")
    rescues = sum(1 for r in appended if r.get("composite_rescued_active_fail_bear"))
    return {
        "ok": True,
        "log_path": str(log_path).replace("\\", "/"),
        "appended": len(appended),
        "fail_appended": fails,
        "composite_rescues": rescues,
        "as_of_kst": as_of_kst,
        "year_month": year_month,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-07")
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--session-date", default=None, help="Single day append")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ns = ap.parse_args()
    as_of = ns.as_of_kst
    if not as_of:
        from datetime import date
        from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before
        as_of = last_krx_trading_day_on_or_before(date.today()) or date.today().isoformat()
    doc = append_feedback(
        year_month=ns.year_month,
        as_of_kst=as_of,
        log_path=ns.log,
        session_date=ns.session_date,
    )
    art_summary = ROOT / "reports/kospi_daily_channel_feedback_latest.json"
    art_summary.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
