#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parallel shadow bundle: composite (bear_triple + conditional_unlock) + FAIL rescue [HYPO].

research_only · send_gate HOLD · auto_apply forbidden · NOT Track A.
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

from scripts.btrack_daily_hero_board_lib_v1 import predict_slot  # noqa: E402
from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import (  # noqa: E402
    _coord_raw_bull,
    _metrics,
    _soft,
)
from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily,
    max_lag_from_rules,
    resolve_prior_foreign_for_gate,
)
from scripts.build_kospi_june2026_neutral_research_bundle_v1 import _resolve_calendar_path  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_hero_shock_gate_shadow_lib_v1 import (  # noqa: E402
    resolve_policy,
    score_shadow_day,
)
from scripts.kospi_weight_counterfactual_lib_v1 import replay_scenario  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_HERO = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_parallel_shadow_bundle_v1_latest.json"
SCHEMA = "kospi_june2026_parallel_shadow_bundle_v1"
BEAR_SCENARIO = "bear_triple_align_boost_v2"
FOREIGN_SELL_THRESHOLD = -25000.0


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _suppressed_bear_count(cal_row: dict[str, Any]) -> int:
    blend = cal_row.get("blend") if isinstance(cal_row.get("blend"), dict) else {}
    n = 0
    for ch in blend.get("channels") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("direction")) == "bear" and float(ch.get("weight") or 0) == 0:
            n += 1
    return n


from scripts.kospi_composite_shadow_lib_v1 import (  # noqa: E402
    composite_active_hold,
    composite_bear_conditional,
)


def fail_rescue_direction(
    *,
    active: str,
    bear_triple: str,
    shock_applied: bool,
    suppressed_bears: int,
    foreign_sell: bool,
) -> str:
    """FAIL-pattern rescue: shock+flow stress or suppressed bears → prefer bear_triple."""
    stress = shock_applied or foreign_sell or suppressed_bears >= 2
    if str(active).lower() == "bull" and stress:
        return bear_triple
    return active


def build_bundle(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    flow: dict[str, float | None],
    hero_cal: dict[str, Any],
    as_of_kst: str,
    year_month: str,
) -> dict[str, Any]:
    cal_by = {str(r.get("session_date")): r for r in (calendar.get("rows") or [])}
    hero_by = {
        str(r.get("session_date") or "")[:10]: r
        for r in (hero_cal.get("rows") or [])
        if isinstance(r, dict) and r.get("session_date")
    }
    scored = [r for r in (eval_doc.get("rows") or []) if str(r.get("session_date")) <= as_of_kst]
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    shock_policy = resolve_policy(rules)

    days: list[dict[str, Any]] = []
    arm_keys = (
        "active_locked",
        "bear_triple_only",
        "conditional_unlock",
        "composite_bear_conditional",
        "composite_active_hold",
        "fail_rescue_triple",
    )
    arm_outcomes: dict[str, list[str]] = {k: [] for k in arm_keys}

    for ev in scored:
        dk = str(ev.get("session_date"))
        cal = cal_by.get(dk, {})
        actual = str(ev.get("actual_direction") or "neutral")
        active = str(ev.get("predicted_direction") or "neutral")
        bear_triple, bear_detail, _ = replay_scenario(
            cal,
            scenario_id=BEAR_SCENARIO,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        coord_raw, coord_mode = _coord_raw_bull(cal, rules, eval_doc)
        prior_ctx = resolve_prior_foreign_for_gate(
            flow, dk, max_lag_calendar_days=max_lag_from_rules(rules)
        )
        prior_fn = prior_ctx.value
        shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
        foreign_sell = (
            prior_ctx.apply_foreign_flow_gate
            and prior_fn is not None
            and prior_fn < FOREIGN_SELL_THRESHOLD
        )
        allow_unlock, blocks = evaluate_conditional_unlock(
            prior_foreign=prior_fn,
            shock_pred=shock_pred,
            foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
            apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
        )
        if prior_ctx.gate_mode == "skipped_stale_forward":
            blocks = list(blocks) + ["flow_gate_skipped_stale_forward"]
        unlock_candidate = active == "neutral" and coord_raw == "bull"
        cond_dir = coord_raw if unlock_candidate and allow_unlock else active

        composite_dir = composite_bear_conditional(
            v2=active,
            bear_triple=bear_triple,
            coord_raw=coord_raw,
            unlock_candidate=unlock_candidate,
            cond_allow=allow_unlock,
        )
        active_hold_dir = composite_active_hold(
            v2=active,
            bear_triple=bear_triple,
            coord_raw=coord_raw,
            unlock_candidate=unlock_candidate,
            cond_allow=allow_unlock,
        )

        hero_row = hero_by.get(dk) or {}
        shock_slots = (hero_row.get("slots") or {}) if isinstance(hero_row.get("slots"), dict) else {}
        shock_day = score_shadow_day(
            session_date=dk,
            active_direction=active,
            actual_direction=actual,
            shock_pred=shock_slots.get("macro_news_shock") or {},
            foreign_flow_pred=shock_slots.get("foreign_flow") or {},
            policy=shock_policy,
        )
        shock_applied = bool((shock_day.get("meta") or {}).get("gate_applied"))
        fail_rescue_dir = fail_rescue_direction(
            active=active,
            bear_triple=bear_triple,
            shock_applied=shock_applied,
            suppressed_bears=_suppressed_bear_count(cal),
            foreign_sell=foreign_sell,
        )

        arms = {
            "active_locked": active,
            "bear_triple_only": bear_triple,
            "conditional_unlock": cond_dir,
            "composite_bear_conditional": composite_dir,
            "composite_active_hold": active_hold_dir,
            "fail_rescue_triple": fail_rescue_dir,
        }
        oc_map = {k: _outcome(d, actual) for k, d in arms.items()}
        for k, oc in oc_map.items():
            arm_outcomes[k].append(oc)

        active_oc = oc_map["active_locked"]
        days.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "daily_return_pct": ev.get("daily_return_pct"),
                "arms": {k: {"direction": arms[k], "outcome": oc_map[k]} for k in arm_keys},
                "meta": {
                    "bear_triple_votes": bear_detail.get("votes"),
                    "coordinator_raw": coord_raw,
                    "coordinator_resolution_mode": coord_mode,
                    "unlock_candidate": unlock_candidate,
                    "conditional_blocks": blocks,
                    "prior_foreign_net_buy": prior_fn,
                    "macro_news_shock_pred": shock_pred,
                    "suppressed_bear_channels": _suppressed_bear_count(cal),
                    "shock_gate_applied": shock_applied,
                },
                "rescued_active_fail": {
                    k: active_oc == "FAIL" and oc_map[k] == "HIT"
                    for k in arm_keys
                    if k != "active_locked"
                },
            }
        )

    summary = {
        k: _metrics([{"outcome": o} for o in arm_outcomes[k]], "outcome")
        for k in arm_keys
    }
    active_soft = float((summary["active_locked"] or {}).get("soft_hit_rate") or 0)
    deltas = {
        k: round(float((summary[k] or {}).get("soft_hit_rate") or 0) - active_soft, 4)
        for k in arm_keys
        if k != "active_locked"
    }
    best = max(
        ((k, deltas[k]) for k in deltas),
        key=lambda x: x[1],
        default=("none", 0.0),
    )
    fail_subset = [d for d in days if d["arms"]["active_locked"]["outcome"] == "FAIL"]
    n_rescue = {
        k: sum(1 for d in fail_subset if d["rescued_active_fail"].get(k))
        for k in deltas
    }

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "policy": {
            "bear_weight_scenario": BEAR_SCENARIO,
            "conditional_unlock_id": "conditional_unlock_morning_v2",
            "fail_rescue_triggers": [
                "active_bull_and_shock_gate",
                "prior_foreign_net_buy_lt_threshold",
                "suppressed_bear_channels_ge_2",
            ],
            "note_ko": "병렬 shadow PoC — apply·Track A 금지.",
        },
        "n_scored_days": len(days),
        "summary": summary,
        "soft_delta_vs_active": deltas,
        "leader_arm": {"id": best[0], "soft_delta_pp": round(best[1] * 100, 2)},
        "active_fail_rescues": n_rescue,
        "session_2026_06_26": next((d for d in days if d["session_date"] == "2026-06-26"), None),
        "days": days,
        "reproduce": (
            f"py scripts/build_kospi_june2026_parallel_shadow_bundle_v1.py "
            f"--year-month {year_month} --as-of-kst {as_of_kst}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--as-of-kst", default="2026-06-26")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--eval-json", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW)
    ap.add_argument("--hero-calendar", type=Path, default=DEFAULT_HERO)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    tag = ns.year_month.replace("-", "")
    if ns.output == DEFAULT_OUT and ns.year_month != "2026-06":
        ns.output = ROOT / f"reports/kospi_{tag}_parallel_shadow_bundle_v1_latest.json"

    cal_path = _resolve_calendar_path(ns.calendar_json, year_month=ns.year_month)
    calendar = _read(cal_path)
    eval_path = ns.eval_json
    if eval_path is None:
        eval_path = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
        if ns.year_month == "2026-06" and not eval_path.is_file():
            eval_path = DEFAULT_EVAL
    eval_doc = _read(eval_path)
    rules = _read(ns.rules_json)
    flow = load_flow_daily(ns.flow_csv)
    hero_cal = _read(ns.hero_calendar)

    doc = build_bundle(
        calendar=calendar,
        eval_doc=eval_doc,
        rules=rules,
        flow=flow,
        hero_cal=hero_cal,
        as_of_kst=ns.as_of_kst,
        year_month=ns.year_month,
    )
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    leader = doc["leader_arm"]
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(ns.output),
                "leader": leader,
                "composite_delta_pp": round(doc["soft_delta_vs_active"].get("composite_bear_conditional", 0) * 100, 2),
                "fail_rescue_delta_pp": round(doc["soft_delta_vs_active"].get("fail_rescue_triple", 0) * 100, 2),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
