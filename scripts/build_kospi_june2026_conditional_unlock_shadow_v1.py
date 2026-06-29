#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conditional 4AI unlock shadow: block neutral→bull when bear-flow/shock gates [HYPO].

Gates (morning-feasible v1):
- prior_foreign_net_buy < 0 → keep v2 (no unlock lift)
- macro_news_shock predicted_binary → keep v2

Compare locked / full_unlock / conditional_unlock on scored June forward + 7 diff days.
research_only · auto_apply forbidden · send_gate HOLD.
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
from scripts.build_kospi_june2026_neutral_research_bundle_v1 import _resolve_calendar_path  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
import scripts.kospi_june_4ai_prophecy_overlay_v1 as overlay  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_UNLOCK_PANEL = ROOT / "reports/kospi_june2026_unlock_diff_macro_panel_v1_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_conditional_unlock_shadow_v1_latest.json"
SCHEMA = "kospi_june2026_conditional_unlock_shadow_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily as _load_flow,
    max_lag_from_rules,
    prior_foreign_raw,
    resolve_and_evaluate_unlock,
    resolve_prior_foreign_for_gate,
)


def _prior_foreign(flow: dict[str, float | None], session_date: str) -> float | None:
    val, _ = prior_foreign_raw(flow, session_date)
    return val


def _soft(outcome: str) -> float:
    if outcome == "HIT":
        return 1.0
    if outcome == "NEUTRAL_DRAW":
        return 0.5
    return 0.0


def _metrics(days: list[dict[str, Any]], key: str) -> dict[str, Any]:
    outcomes = [str(d.get(key) or "") for d in days if d.get(key)]
    n_dir = sum(1 for o in outcomes if o in ("HIT", "FAIL"))
    hits = sum(1 for o in outcomes if o == "HIT")
    return {
        "n": len(outcomes),
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round(sum(_soft(o) for o in outcomes) / len(outcomes), 4) if outcomes else None,
        "hit": hits,
        "fail": sum(1 for o in outcomes if o == "FAIL"),
        "neutral_draw": sum(1 for o in outcomes if o == "NEUTRAL_DRAW"),
    }


def _coord_raw_bull(calendar_row: dict[str, Any], rules: dict[str, Any], eval_doc: dict[str, Any]) -> tuple[str, str]:
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    coord_base = rules.get("four_ai_coordinator_policy") if isinstance(rules.get("four_ai_coordinator_policy"), dict) else {}
    unlocked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": False}
    doc = overlay.build_4ai_report(
        {"rows": [calendar_row], "year_month": "2026-06"},
        eval_doc=eval_doc,
        blend_policy=blend_policy,
        coordinator_policy=unlocked_pol,
    )
    row = (doc.get("rows") or [{}])[0]
    ab = row.get("absolute_balance") if isinstance(row.get("absolute_balance"), dict) else {}
    raw = str(ab.get("coordinator_direction") or row.get("four_ai_direction") or "neutral")
    mode = str(ab.get("resolution_mode") or row.get("weight_field") or "")
    return raw, mode


# evaluate_conditional_unlock imported from kospi_forward_flow_gate_lib_v1


def build_shadow(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    flow: dict[str, float | None],
    diff_dates: set[str],
    as_of_kst: str,
    foreign_sell_threshold: float = -25000.0,
) -> dict[str, Any]:
    cal_by = {str(r.get("session_date")): r for r in (calendar.get("rows") or [])}
    scored = [r for r in (eval_doc.get("rows") or []) if str(r.get("session_date")) <= as_of_kst]
    days: list[dict[str, Any]] = []

    for ev in scored:
        dk = str(ev.get("session_date"))
        cal = cal_by.get(dk, {})
        v2 = str(ev.get("predicted_direction") or cal.get("predicted_direction") or "neutral")
        actual = str(ev.get("actual_direction") or "neutral")
        coord_raw, coord_mode = _coord_raw_bull(cal, rules, eval_doc)
        prior_ctx = resolve_prior_foreign_for_gate(
            flow, dk, max_lag_calendar_days=max_lag_from_rules(rules)
        )
        prior_fn = prior_ctx.value
        shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
        unlock_candidate = v2 == "neutral" and coord_raw == "bull"

        locked_dir = v2
        full_unlock_dir = coord_raw if unlock_candidate else v2
        allow, block_reasons = evaluate_conditional_unlock(
            prior_foreign=prior_fn,
            shock_pred=shock_pred,
            foreign_sell_threshold=foreign_sell_threshold,
            apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
        )
        if prior_ctx.gate_mode == "skipped_stale_forward":
            block_reasons = list(block_reasons) + ["flow_gate_skipped_stale_forward"]
        if unlock_candidate and allow:
            cond_dir = coord_raw
            cond_applied = True
        else:
            cond_dir = v2
            cond_applied = False

        locked_oc = str(ev.get("outcome") or _outcome(locked_dir, actual))
        full_oc = _outcome(full_unlock_dir, actual)
        cond_oc = _outcome(cond_dir, actual)

        days.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "daily_return_pct": ev.get("daily_return_pct"),
                "in_unlock_diff_panel": dk in diff_dates,
                "unlock_candidate": unlock_candidate,
                "v2_direction": v2,
                "coordinator_raw": coord_raw,
                "coordinator_resolution_mode": coord_mode,
                "prior_foreign_net_buy": prior_fn,
                "macro_news_shock_pred": shock_pred,
                "conditional_blocks": block_reasons,
                "conditional_unlock_applied": cond_applied,
                "arms": {
                    "locked_v2": {"direction": locked_dir, "outcome": locked_oc},
                    "full_unlock": {"direction": full_unlock_dir, "outcome": full_oc},
                    "conditional_unlock": {"direction": cond_dir, "outcome": cond_oc},
                },
                "conditional_beats_full_unlock": _soft(cond_oc) > _soft(full_oc),
                "conditional_beats_locked": _soft(cond_oc) > _soft(locked_oc),
            }
        )

    diff_days = [d for d in days if d.get("in_unlock_diff_panel")]
    unlock_candidates = [d for d in days if d.get("unlock_candidate")]

    full_on_candidates = [
        {"outcome": d["arms"]["full_unlock"]["outcome"]} for d in unlock_candidates
    ]
    cond_on_candidates = [
        {"outcome": d["arms"]["conditional_unlock"]["outcome"]} for d in unlock_candidates
    ]
    locked_on_candidates = [
        {"outcome": d["arms"]["locked_v2"]["outcome"]} for d in unlock_candidates
    ]

    n_blocked = sum(1 for d in unlock_candidates if not d.get("conditional_unlock_applied"))
    n_block_saves_fail = sum(
        1
        for d in unlock_candidates
        if not d.get("conditional_unlock_applied")
        and d["arms"]["full_unlock"]["outcome"] == "FAIL"
        and d["arms"]["conditional_unlock"]["outcome"] != "FAIL"
    )

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": calendar.get("year_month") or "2026-06",
        "as_of_kst": as_of_kst,
        "policy": {
            "id": "conditional_unlock_morning_v2",
            "apply_when": "v2_neutral AND coordinator_raw_bull",
            "block_if": [
                "prior_foreign_net_buy < foreign_sell_threshold",
                "macro_news_shock_pred AND prior_foreign_net_buy < 0",
            ],
            "foreign_sell_threshold": foreign_sell_threshold,
            "note_ko": "장전 feasible: T-1 외인 대량 순매도·shock+순매도 시 balance_bull 승격 억제. apply 금지.",
        },
        "n_scored_days": len(days),
        "n_unlock_candidates": len(unlock_candidates),
        "n_conditional_blocks": n_blocked,
        "n_block_prevented_full_unlock_fail": n_block_saves_fail,
        "all_scored": {
            "locked_v2": _metrics(
                [{"outcome": d["arms"]["locked_v2"]["outcome"]} for d in days],
                "outcome",
            ),
            "full_unlock": _metrics(
                [{"outcome": d["arms"]["full_unlock"]["outcome"]} for d in days],
                "outcome",
            ),
            "conditional_unlock": _metrics(
                [{"outcome": d["arms"]["conditional_unlock"]["outcome"]} for d in days],
                "outcome",
            ),
        },
        "unlock_candidate_subset": {
            "locked_v2": _metrics(locked_on_candidates, "outcome"),
            "full_unlock": _metrics(full_on_candidates, "outcome"),
            "conditional_unlock": _metrics(cond_on_candidates, "outcome"),
        },
        "diff_panel_subset": {
            "n_days": len(diff_days),
            "locked_v2": _metrics(
                [{"outcome": d["arms"]["locked_v2"]["outcome"]} for d in diff_days],
                "outcome",
            ),
            "full_unlock": _metrics(
                [{"outcome": d["arms"]["full_unlock"]["outcome"]} for d in diff_days],
                "outcome",
            ),
            "conditional_unlock": _metrics(
                [{"outcome": d["arms"]["conditional_unlock"]["outcome"]} for d in diff_days],
                "outcome",
            ),
        },
        "days": days,
        "verdict_ko": (
            f"unlock 후보 {len(unlock_candidates)}일 중 조건부 차단 {n_blocked}일 · "
            f"full FAIL 방지 {n_block_saves_fail}건. Track A·live apply 금지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--unlock-panel-json", type=Path, default=DEFAULT_UNLOCK_PANEL)
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--foreign-sell-threshold", type=float, default=-25000.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _default_as_of_kst

    eval_doc = _read(args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json)
    panel = _read(args.unlock_panel_json if args.unlock_panel_json.is_absolute() else ROOT / args.unlock_panel_json)
    diff_dates = {str(d.get("session_date")) for d in (panel.get("days") or []) if d.get("session_date")}
    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month).resolve()
    calendar = _read(cal_path)
    rules = _read(DEFAULT_RULES)
    flow = _load_flow(DEFAULT_FLOW)
    as_of = args.as_of_kst or _default_as_of_kst()

    doc = build_shadow(
        calendar=calendar,
        eval_doc=eval_doc,
        rules=rules,
        flow=flow,
        diff_dates=diff_dates,
        as_of_kst=as_of,
        foreign_sell_threshold=args.foreign_sell_threshold,
    )

    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    uc = doc["unlock_candidate_subset"]
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "n_scored": doc["n_scored_days"],
                "full_unlock_hr": uc["full_unlock"].get("directional_hit_rate"),
                "conditional_hr": uc["conditional_unlock"].get("directional_hit_rate"),
                "fail_prevented": doc["n_block_prevented_full_unlock_fail"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
