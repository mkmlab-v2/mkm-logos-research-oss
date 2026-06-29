#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dual-path conflict shadow AB: per_date baseline vs static bear/composite on conflict [HYPO]."""

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
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.build_kospi_june2026_channel_input_audit_v1 import _momentum_from_row, _replay_row  # noqa: E402
from scripts.kospi_dual_path_conflict_shadow_lib_v1 import (  # noqa: E402
    FOREIGN_SELL_THRESHOLD,
    FOREIGN_WEAK_FLOW_GUARD,
    build_composite_for_conflict,
    detect_macro_bear_session_bull_trap,
    detect_momentum_perdate_bull_conflict,
    dual_path_direction,
    dual_path_v2_direction,
    should_apply_tier_a_bear_rescue,
)
from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily,
    max_lag_from_rules,
    resolve_prior_foreign_for_gate,
)
from scripts.kospi_hero_shock_gate_shadow_lib_v1 import _metrics_from_outcomes  # noqa: E402
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    DEFAULT_MACRO_BACKFILL_JSONL,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    load_per_date_lens_bundle,
    per_date_lenses_for_session,
)
from scripts.kospi_weight_counterfactual_lib_v1 import (  # noqa: E402
    ACTIVE_WEIGHTS,
    WEIGHT_SCENARIOS,
    replay_scenario,
    replay_scenario_per_date,
)

BEAR_SCENARIO = "bear_triple_align_boost_v2"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_FLOW = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/kospi_dual_path_conflict_shadow_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paths_for_month(year_month: str) -> tuple[Path, Path, Path]:
    tag = year_month.replace("-", "")
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    ev = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    if year_month == "2026-06" and not ev.is_file():
        ev = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    out = ROOT / f"reports/kospi_{tag}_dual_path_conflict_shadow_v1_latest.json"
    return cal, ev, out


def _replay_per_date_active(
    cal_row: dict[str, Any],
    *,
    per_static: dict[str, Any],
    ensemble_by_date: dict[str, dict[str, Any]],
    neutral_band: float,
    blend_policy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    from scripts.kospi_june2026_multilens_blend_v1 import blend_v2_multilens

    dk = str(cal_row.get("session_date"))
    pred, _, detail = blend_v2_multilens(
        session_map=str(cal_row.get("session_mapping_target") or "sideways"),
        session_score=float(cal_row.get("session_direction_score") or 0.0),
        momentum_dir=_momentum_from_row(cal_row),
        static_lenses=per_static,
        ensemble_row=ensemble_by_date.get(dk),
        weights=dict(ACTIVE_WEIGHTS),
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    return pred, detail


def build_shadow(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    macro_gate_by_day: dict[str, dict[str, Any]] | None,
    flow: dict[str, float | None],
    as_of_kst: str,
    year_month: str,
    min_suppressed_bear: int = 2,
) -> dict[str, Any]:
    from scripts.kospi_june2026_multilens_blend_v1 import load_ensemble_kospi_per_date, load_static_lenses

    cal_by = {str(r.get("session_date"))[:10]: r for r in (calendar.get("rows") or []) if r.get("session_date")}
    scored = [r for r in (eval_doc.get("rows") or []) if str(r.get("session_date")) <= as_of_kst[:10]]
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    baseline_static = load_static_lenses()
    trading_days = list(cal_by.keys())
    ens = load_ensemble_kospi_per_date(trading_days)
    macro_off_weights = WEIGHT_SCENARIOS["macro_off_session_half"]["weights"]

    arm_keys = (
        "active_locked",
        "per_date_baseline",
        "per_date_baseline_macro",
        "static_bear_triple",
        "dual_path_bear_triple",
        "dual_path_composite",
        "dual_path_v2_router",
    )
    days: list[dict[str, Any]] = []
    arm_outcomes: dict[str, list[str]] = {k: [] for k in arm_keys}

    for ev in scored:
        dk = str(ev.get("session_date"))[:10]
        cal = cal_by.get(dk, {})
        if not cal:
            continue
        actual = str(ev.get("actual_direction") or "neutral")
        active = str(ev.get("predicted_direction") or "neutral")

        per_static = per_date_lenses_for_session(
            dk,
            myeongni_by_day=myeongni_by_day,
            sasang_by_day=sasang_by_day,
            macro_gate_by_day=None,
            baseline=baseline_static,
        )
        per_static_macro = per_date_lenses_for_session(
            dk,
            myeongni_by_day=myeongni_by_day,
            sasang_by_day=sasang_by_day,
            macro_gate_by_day=macro_gate_by_day,
            baseline=baseline_static,
        )
        per_date_dir, per_detail = _replay_per_date_active(
            cal,
            per_static=per_static,
            ensemble_by_date=ens,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        per_date_macro_dir, per_macro_detail = _replay_per_date_active(
            cal,
            per_static=per_static_macro,
            ensemble_by_date=ens,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        static_bear, bear_detail, _ = replay_scenario(
            cal,
            scenario_id=BEAR_SCENARIO,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        per_bear, _, _ = replay_scenario_per_date(
            cal,
            scenario_id=BEAR_SCENARIO,
            myeongni_by_day=myeongni_by_day,
            sasang_by_day=sasang_by_day,
            ensemble_by_date=ens,
            baseline_static=baseline_static,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )

        conflict, conflict_reasons = detect_momentum_perdate_bull_conflict(
            cal,
            per_static,
            active_direction=active,
            min_suppressed_bear=min_suppressed_bear,
        )

        coord_raw, coord_mode = _coord_raw_bull(cal, rules, eval_doc)
        prior_ctx = resolve_prior_foreign_for_gate(
            flow, dk, max_lag_calendar_days=max_lag_from_rules(rules)
        )
        prior_fn = prior_ctx.value
        from scripts.btrack_daily_hero_board_lib_v1 import predict_slot

        shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
        allow_unlock, blocks = evaluate_conditional_unlock(
            prior_foreign=prior_fn,
            shock_pred=shock_pred,
            foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
            apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
        )
        unlock_candidate = active == "neutral" and coord_raw == "bull"
        composite_dir = build_composite_for_conflict(
            active=active,
            bear_triple=static_bear,
            coord_raw=coord_raw,
            unlock_candidate=unlock_candidate,
            cond_allow=allow_unlock,
        )

        dual_bear = dual_path_direction(
            conflict=conflict,
            per_date_active_dir=per_date_dir,
            static_bear_triple_dir=static_bear,
            router_mode="bear_triple_on_conflict",
        )
        dual_comp = dual_path_direction(
            conflict=conflict,
            per_date_active_dir=per_date_dir,
            static_bear_triple_dir=static_bear,
            composite_dir=composite_dir,
            router_mode="composite_on_conflict",
        )

        tier_b, tier_b_reasons = detect_macro_bear_session_bull_trap(
            cal,
            per_static_macro,
            active_direction=active,
            min_suppressed_bear=min_suppressed_bear,
        )
        tier_a_apply, tier_a_guard = should_apply_tier_a_bear_rescue(
            tier_a_conflict=conflict,
            prior_foreign_net_buy=prior_fn,
        )
        macro_off_dir, macro_off_detail = _replay_row(
            cal,
            static_lenses=per_static_macro,
            ensemble_by_date=ens,
            weights=macro_off_weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        dual_v2_dir, dual_v2_route = dual_path_v2_direction(
            tier_a_apply=tier_a_apply,
            tier_b_conflict=tier_b and not tier_a_apply,
            per_date_baseline_dir=per_date_macro_dir,
            static_bear_triple_dir=static_bear,
            macro_off_per_date_dir=macro_off_dir,
        )

        arms = {
            "active_locked": active,
            "per_date_baseline": per_date_dir,
            "per_date_baseline_macro": per_date_macro_dir,
            "static_bear_triple": static_bear,
            "dual_path_bear_triple": dual_bear,
            "dual_path_composite": dual_comp,
            "dual_path_v2_router": dual_v2_dir,
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
                "conflict_detected": conflict,
                "conflict_reason_codes": conflict_reasons,
                "tier_b_detected": tier_b,
                "tier_b_reason_codes": tier_b_reasons,
                "tier_a_apply": tier_a_apply,
                "tier_a_guard_codes": tier_a_guard,
                "dual_path_v2_route": dual_v2_route,
                "arms": {k: {"direction": arms[k], "outcome": oc_map[k]} for k in arm_keys},
                "meta": {
                    "momentum": _momentum_from_row(cal),
                    "per_date_myeongni": (per_static_macro.get("myeongni_independent") or {}).get("direction"),
                    "per_date_sasang": (per_static_macro.get("sasang") or {}).get("direction"),
                    "per_date_macro": (per_static_macro.get("macro") or {}).get("direction"),
                    "per_date_baseline_votes": per_detail.get("votes"),
                    "per_date_baseline_macro_votes": per_macro_detail.get("votes"),
                    "macro_off_votes": macro_off_detail.get("votes"),
                    "static_bear_triple_votes": bear_detail.get("votes"),
                    "per_date_bear_triple_direction": per_bear,
                    "coordinator_raw": coord_raw,
                    "coordinator_resolution_mode": coord_mode,
                    "conditional_blocks": blocks,
                    "prior_foreign_net_buy": prior_fn,
                },
                "rescued_active_fail": {
                    k: active_oc == "FAIL" and oc_map[k] == "HIT" for k in arm_keys if k != "active_locked"
                },
            }
        )

    summary = {k: _metrics_from_outcomes(arm_outcomes[k]) for k in arm_keys}
    active_soft = float((summary["active_locked"] or {}).get("soft_hit_rate") or 0)
    deltas = {
        k: round(float((summary[k] or {}).get("soft_hit_rate") or 0) - active_soft, 4)
        for k in arm_keys
        if k != "active_locked"
    }
    per_date_soft = float((summary["per_date_baseline"] or {}).get("soft_hit_rate") or 0)
    dual_deltas_vs_per_date = {
        k: round(float((summary[k] or {}).get("soft_hit_rate") or 0) - per_date_soft, 4)
        for k in ("dual_path_bear_triple", "dual_path_composite", "dual_path_v2_router")
    }

    conflict_days = [d for d in days if d.get("conflict_detected")]
    tier_b_days = [d for d in days if d.get("tier_b_detected")]
    fail_days = [d for d in days if d["arms"]["active_locked"]["outcome"] == "FAIL"]
    n_conflict = len(conflict_days)
    n_tier_b = len(tier_b_days)
    n_conflict_rescue_bear = sum(1 for d in conflict_days if d["rescued_active_fail"].get("dual_path_bear_triple"))
    n_conflict_rescue_comp = sum(1 for d in conflict_days if d["rescued_active_fail"].get("dual_path_composite"))
    n_v2_rescue_fail = sum(1 for d in fail_days if d["rescued_active_fail"].get("dual_path_v2_router"))

    leader = max(
        ((k, deltas[k]) for k in deltas if k.startswith("dual_path")),
        key=lambda x: x[1],
        default=(None, None),
    )
    v2_soft = (summary.get("dual_path_v2_router") or {}).get("soft_hit_rate")

    return {
        "schema": "kospi_dual_path_conflict_shadow_v2",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "production_apply_authorized": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "n_scored": len(days),
        "conflict_policy": {
            "min_suppressed_bear": min_suppressed_bear,
            "tier_a_trigger_ko": "momentum bear + per_date myeongni·sasang bull + active bull + suppressed bear≥N",
            "tier_a_flow_guard_ko": f"foreign_sell<{FOREIGN_SELL_THRESHOLD} OR prior_foreign≤{FOREIGN_WEAK_FLOW_GUARD}",
            "tier_b_trigger_ko": "per_date macro bear + session bull + active bull + suppressed bear≥N",
            "tier_b_router": "macro_off_session_half + per_date macro JSONL",
            "router_modes": ["bear_triple_on_conflict", "composite_on_conflict", "dual_path_v2_router"],
        },
        "summary": summary,
        "delta_vs_active_soft": deltas,
        "delta_dual_vs_per_date_baseline": dual_deltas_vs_per_date,
        "leader_dual_path": {"id": leader[0], "soft_delta_pp": leader[1]},
        "recommended_shadow_arm": "dual_path_v2_router",
        "conflict_stats": {
            "n_conflict_days": n_conflict,
            "n_tier_b_days": n_tier_b,
            "n_active_fail": len(fail_days),
            "n_conflict_on_fail_days": sum(1 for d in fail_days if d.get("conflict_detected")),
            "n_tier_b_on_fail_days": sum(1 for d in fail_days if d.get("tier_b_detected")),
            "n_rescued_on_conflict_dual_bear": n_conflict_rescue_bear,
            "n_rescued_on_conflict_dual_composite": n_conflict_rescue_comp,
            "n_rescued_active_fail_v2": n_v2_rescue_fail,
            "n_residual_fail_v2": sum(1 for d in fail_days if d["arms"]["dual_path_v2_router"]["outcome"] == "FAIL"),
        },
        "fail_day_detail": [
            {
                "session_date": d["session_date"],
                "conflict_detected": d.get("conflict_detected"),
                "actual": d["actual_direction"],
                "active": d["arms"]["active_locked"]["direction"],
                "per_date_baseline": d["arms"]["per_date_baseline"]["direction"],
                "dual_path_bear_triple": d["arms"]["dual_path_bear_triple"]["direction"],
                "dual_path_composite": d["arms"]["dual_path_composite"]["direction"],
                "dual_path_v2_router": d["arms"]["dual_path_v2_router"]["direction"],
                "dual_path_v2_route": d.get("dual_path_v2_route"),
                "outcomes": {k: d["arms"][k]["outcome"] for k in arm_keys},
            }
            for d in fail_days
        ],
        "days": days,
        "headline_ko": (
            f"{year_month} n={len(days)} dual_path_v2 {v2_soft} "
            f"(Δ active {deltas.get('dual_path_v2_router')} · tierB {n_tier_b}일) — apply HOLD"
            if days
            else f"{year_month} n_scored=0 — dual path pending"
        ),
        "reproduce": (
            f"py scripts/build_kospi_dual_path_conflict_shadow_v1.py "
            f"--year-month {year_month} --as-of-kst {as_of_kst}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--calendar", type=Path, default=None)
    ap.add_argument("--eval", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--min-suppressed-bear", type=int, default=2)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()

    if not ns.as_of_kst:
        from datetime import date

        from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

        ns.as_of_kst = last_krx_trading_day_on_or_before(date.today()) or date.today().isoformat()

    cal_p, ev_p, month_out = _paths_for_month(ns.year_month)
    cal_p = ns.calendar or cal_p
    ev_p = ns.eval or ev_p
    out_p = ns.output if ns.output.is_absolute() else ROOT / ns.output
    if ns.output == DEFAULT_OUT and ns.year_month != "2026-06":
        out_p = month_out

    my_by, sa_by, macro_by, jsonl_meta = load_per_date_lens_bundle(
        ns.myeongni_jsonl, ns.sasang_jsonl, macro_backfill_jsonl=DEFAULT_MACRO_BACKFILL_JSONL
    )
    if not my_by or not sa_by:
        raise SystemExit("per_date JSONL missing")

    doc = build_shadow(
        calendar=_read(cal_p),
        eval_doc=_read(ev_p),
        rules=_read(ns.rules_json if ns.rules_json.is_absolute() else ROOT / ns.rules_json),
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        macro_gate_by_day=macro_by,
        flow=load_flow_daily(ns.flow_csv),
        as_of_kst=ns.as_of_kst,
        year_month=ns.year_month,
        min_suppressed_bear=ns.min_suppressed_bear,
    )
    doc["per_date_jsonl"] = jsonl_meta

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_dual_path_conflict_shadow_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": doc["n_scored"],
                "n_conflict": doc["conflict_stats"]["n_conflict_days"],
                "n_tier_b": doc["conflict_stats"]["n_tier_b_days"],
                "dual_v2_soft": doc["summary"]["dual_path_v2_router"].get("soft_hit_rate"),
                "delta_vs_active": doc["delta_vs_active_soft"].get("dual_path_v2_router"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
