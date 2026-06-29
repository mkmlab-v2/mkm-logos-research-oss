#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stress-day cross: per-lens counterfactual + 4AI lock/unlock on market_stress subset [HYPO]."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_neutral_research_bundle_v1 import (  # noqa: E402
    _resolve_calendar_path,
    four_ai_counterfactual,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import eval_calendar  # noqa: E402
import scripts.kospi_june_4ai_prophecy_overlay_v1 as overlay  # noqa: E402

DEFAULT_STRESS = ROOT / "reports/kospi_june2026_stress_conditional_shadow_replay_v1_latest.json"
DEFAULT_LENS_CF = ROOT / "reports/kospi_june2026_per_date_lens_counterfactual_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_stress_shadow_lens_4ai_cross_v1_latest.json"
SCHEMA = "kospi_june2026_stress_shadow_lens_4ai_cross_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _soft(outcome: str) -> float:
    if outcome == "HIT":
        return 1.0
    if outcome == "NEUTRAL_DRAW":
        return 0.5
    return 0.0


def _metrics(days: list[dict[str, Any]], outcome_key: str) -> dict[str, Any]:
    outcomes = [str(d.get(outcome_key) or "") for d in days if d.get(outcome_key)]
    n_dir = sum(1 for o in outcomes if o in ("HIT", "FAIL"))
    hits = sum(1 for o in outcomes if o == "HIT")
    return {
        "n_days": len(days),
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round(sum(_soft(o) for o in outcomes) / len(outcomes), 4) if outcomes else None,
        "hit": hits,
        "fail": sum(1 for o in outcomes if o == "FAIL"),
        "neutral_draw": sum(1 for o in outcomes if o == "NEUTRAL_DRAW"),
    }


def _eval_overlay_on_dates(
    calendar: dict[str, Any],
    overlay_doc: dict[str, Any],
    *,
    stress_dates: set[str],
    as_of_kst: str,
) -> dict[str, Any]:
    by_date = {str(r.get("session_date")): r for r in overlay_doc.get("rows") or []}
    cal_copy = copy.deepcopy(calendar)
    for row in cal_copy.get("rows") or []:
        dk = str(row.get("session_date") or "")
        if dk not in stress_dates:
            continue
        orow = by_date.get(dk) or {}
        if orow.get("four_ai_direction") is not None:
            row["predicted_direction"] = str(orow["four_ai_direction"])
    ev = eval_calendar(cal_copy, as_of_kst=as_of_kst)
    stress_rows = [r for r in ev.get("rows") or [] if str(r.get("session_date")) in stress_dates]
    return {
        "n_scored_stress": len(stress_rows),
        "metrics_stress": _metrics(
            [{"outcome": r.get("outcome")} for r in stress_rows],
            "outcome",
        ),
        "days": stress_rows,
    }


def build_cross(
    *,
    stress_doc: dict[str, Any],
    lens_cf_doc: dict[str, Any],
    calendar: dict[str, Any],
    rules: dict[str, Any],
    eval_doc: dict[str, Any],
    as_of_kst: str,
) -> dict[str, Any]:
    stress_dates = {
        str(d.get("session_date"))
        for d in (stress_doc.get("days") or [])
        if isinstance(d, dict) and d.get("market_stress")
    }
    lens_days = [
        d
        for d in ((lens_cf_doc.get("summary") or {}).get("scored_forward") or {}).get("days") or []
        if str(d.get("session_date")) in stress_dates
    ]

    lens_rescue = sum(
        1
        for d in lens_days
        if d.get("active_outcome") == "FAIL" and d.get("counterfactual_outcome") == "HIT"
    )
    lens_active_fail = sum(1 for d in lens_days if d.get("active_outcome") == "FAIL")

    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    coord_base = rules.get("four_ai_coordinator_policy") if isinstance(rules.get("four_ai_coordinator_policy"), dict) else {}
    locked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": True}
    unlocked_pol = {**coord_base, "lock_coordinator_to_v2_calendar": False}

    locked_overlay = overlay.build_4ai_report(calendar, eval_doc=eval_doc, blend_policy=blend_policy, coordinator_policy=locked_pol)
    unlocked_overlay = overlay.build_4ai_report(calendar, eval_doc=eval_doc, blend_policy=blend_policy, coordinator_policy=unlocked_pol)

    v2_stress_rows = [
        r for r in eval_doc.get("rows") or [] if str(r.get("session_date")) in stress_dates
    ]
    v2_stress = {
        "n_scored_stress": len(v2_stress_rows),
        "metrics_stress": _metrics(
            [{"outcome": r.get("outcome")} for r in v2_stress_rows],
            "outcome",
        ),
        "days": v2_stress_rows,
    }
    locked_stress = _eval_overlay_on_dates(calendar, locked_overlay, stress_dates=stress_dates, as_of_kst=as_of_kst)
    unlocked_stress = _eval_overlay_on_dates(calendar, unlocked_overlay, stress_dates=stress_dates, as_of_kst=as_of_kst)

    cf = four_ai_counterfactual(calendar, evolution_path=DEFAULT_RULES, eval_doc=eval_doc)
    cf_stress_diffs = [d for d in (cf.get("diff_rows") or []) if str(d.get("session_date")) in stress_dates]

    shadow_days = [d for d in (stress_doc.get("days") or []) if d.get("market_stress")]

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": stress_doc.get("year_month"),
        "as_of_kst": as_of_kst,
        "n_market_stress_days": len(stress_dates),
        "stress_policy_ref": stress_doc.get("stress_policy"),
        "shadow_field_momentum_on_stress": {
            "candidate_id": stress_doc.get("shadow_candidate_id"),
            "metrics": stress_doc.get("stress_subset"),
            "n_shadow_rescue_active_fail": (stress_doc.get("active_fail_subset") or {}).get(
                "n_shadow_rescue_on_active_fail"
            ),
        },
        "per_lens_counterfactual_on_stress": {
            "n_days": len(lens_days),
            "active": _metrics(lens_days, "active_outcome"),
            "counterfactual": _metrics(lens_days, "counterfactual_outcome"),
            "n_lens_rescue_on_active_fail": lens_rescue,
            "n_active_fail": lens_active_fail,
            "days": lens_days,
        },
        "four_ai_lock_unlock_on_stress": {
            "v2_only": v2_stress.get("metrics_stress"),
            "four_ai_locked": locked_stress.get("metrics_stress"),
            "four_ai_unlocked": unlocked_stress.get("metrics_stress"),
            "soft_delta_unlock_minus_v2": round(
                float((unlocked_stress.get("metrics_stress") or {}).get("soft_hit_rate") or 0)
                - float((v2_stress.get("metrics_stress") or {}).get("soft_hit_rate") or 0),
                4,
            )
            if unlocked_stress.get("metrics_stress") and v2_stress.get("metrics_stress")
            else None,
            "n_lock_unlock_diffs_on_stress": len(cf_stress_diffs),
            "diff_rows": cf_stress_diffs,
        },
        "stress_shadow_days": shadow_days,
        "note_ko": (
            f"market_stress {len(stress_dates)}일 — lens CF rescue {lens_rescue}/{lens_active_fail} FAIL, "
            f"4AI unlock Δ soft {((unlocked_stress.get('metrics_stress') or {}).get('soft_hit_rate'))}. "
            "연구 전용·apply 금지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--stress-json", type=Path, default=DEFAULT_STRESS)
    ap.add_argument("--lens-cf-json", type=Path, default=DEFAULT_LENS_CF)
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    from scripts.eval_kospi_june2026_daily_prophecy_v1 import _default_as_of_kst

    stress = _read(args.stress_json if args.stress_json.is_absolute() else ROOT / args.stress_json)
    if stress.get("schema") != "kospi_june2026_stress_conditional_shadow_replay_v1":
        raise SystemExit(f"invalid stress replay: {args.stress_json}")

    lens_cf = _read(args.lens_cf_json if args.lens_cf_json.is_absolute() else ROOT / args.lens_cf_json)
    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month).resolve()
    calendar = _read(cal_path)
    rules = _read(DEFAULT_RULES)
    eval_doc = _read(args.eval_json if args.eval_json.is_absolute() else ROOT / args.eval_json)
    as_of = args.as_of_kst or _default_as_of_kst()

    doc = build_cross(
        stress_doc=stress,
        lens_cf_doc=lens_cf,
        calendar=calendar,
        rules=rules,
        eval_doc=eval_doc,
        as_of_kst=as_of,
    )
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "n_market_stress": doc["n_market_stress_days"],
                "lens_rescue": doc["per_lens_counterfactual_on_stress"]["n_lens_rescue_on_active_fail"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
