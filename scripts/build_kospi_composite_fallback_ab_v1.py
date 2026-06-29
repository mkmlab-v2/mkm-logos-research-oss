#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composite fallback A/B: bear_conditional vs active_hold on calendar panel [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_daily_hero_board_lib_v1 import predict_slot  # noqa: E402
from scripts.build_kospi_june2026_conditional_unlock_shadow_v1 import _coord_raw_bull  # noqa: E402
from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _paths_for_month, build_calendar  # noqa: E402
from scripts.build_kospi_june2026_parallel_shadow_bundle_v1 import (  # noqa: E402
    BEAR_SCENARIO,
    _metrics,
    _soft,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_composite_shadow_lib_v1 import composite_active_hold, composite_bear_conditional  # noqa: E402
from scripts.kospi_forward_flow_gate_lib_v1 import (  # noqa: E402
    evaluate_conditional_unlock,
    load_flow_daily,
    max_lag_from_rules,
    resolve_prior_foreign_for_gate,
    summarize_flow_gate_usage,
)
from scripts.kospi_weight_counterfactual_lib_v1 import replay_scenario  # noqa: E402

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_composite_fallback_ab_v1_latest.json"
FOREIGN_SELL_THRESHOLD = -25000.0


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_calendar(ym: str) -> dict[str, Any]:
    path, _ = _paths_for_month(ym)
    if path.is_file():
        return _read(path)
    return build_calendar(year_month=ym, skip_panel=True, profile="v2_multilens")


def _eval_rows(ym: str, as_of: str) -> dict[str, dict[str, Any]]:
    tag = ym.replace("-", "")
    candidates = [
        ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json",
        ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json" if ym == "2026-06" else None,
    ]
    doc: dict[str, Any] = {}
    for p in candidates:
        if p and p.is_file():
            doc = _read(p)
            break
    return {
        str(r.get("session_date")): r
        for r in (doc.get("rows") or [])
        if str(r.get("session_date")) <= as_of
    }


def _composite_for_day(
    cal_row: dict[str, Any],
    *,
    rules: dict[str, Any],
    flow: dict[str, float | None],
    eval_stub: dict[str, Any],
    composite_fn: Callable[..., str],
) -> tuple[str, str, dict[str, Any]]:
    dk = str(cal_row.get("session_date"))
    active = str(cal_row.get("predicted_direction") or "neutral")
    nb = float(rules.get("neutral_band", 0.06))
    bp = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    bear_triple, _, _ = replay_scenario(cal_row, scenario_id=BEAR_SCENARIO, neutral_band=nb, blend_policy=bp)
    coord_raw, coord_mode = _coord_raw_bull(cal_row, rules, eval_stub)
    prior_ctx = resolve_prior_foreign_for_gate(flow, dk, max_lag_calendar_days=max_lag_from_rules(rules))
    shock_pred = bool((predict_slot("macro_news_shock", dk) or {}).get("predicted_binary"))
    allow, blocks = evaluate_conditional_unlock(
        prior_foreign=prior_ctx.value,
        shock_pred=shock_pred,
        foreign_sell_threshold=FOREIGN_SELL_THRESHOLD,
        apply_foreign_flow_gate=prior_ctx.apply_foreign_flow_gate,
    )
    if prior_ctx.gate_mode == "skipped_stale_forward":
        blocks = list(blocks) + ["flow_gate_skipped_stale_forward"]
    unlock = active == "neutral" and coord_raw == "bull"
    comp = composite_fn(
        v2=active,
        bear_triple=bear_triple,
        coord_raw=coord_raw,
        unlock_candidate=unlock,
        cond_allow=allow,
    )
    return active, comp, {
        "flow_gate_mode": prior_ctx.gate_mode,
        "blocks": blocks,
        "unlock_candidate": unlock,
        "coord_mode": coord_mode,
    }


def build_ab(
    *,
    year_months: list[str],
    as_of_kst: str,
    rules: dict[str, Any],
    flow: dict[str, float | None],
) -> dict[str, Any]:
    eval_stub: dict[str, Any] = {"rows": []}
    arms = {
        "composite_bear_conditional": composite_bear_conditional,
        "composite_active_hold": composite_active_hold,
    }
    day_rows: list[dict[str, Any]] = []
    arm_outcomes: dict[str, list[str]] = {k: [] for k in arms}

    for ym in year_months:
        cal = _load_calendar(ym)
        eval_by = _eval_rows(ym, as_of_kst)
        for cr in cal.get("rows") or []:
            dk = str(cr.get("session_date"))
            if dk > as_of_kst:
                continue
            ev = eval_by.get(dk)
            actual = str((ev or {}).get("actual_direction") or "")
            if not actual:
                continue
            row: dict[str, Any] = {"session_date": dk, "year_month": ym, "actual_direction": actual}
            for arm_id, fn in arms.items():
                active, comp, meta = _composite_for_day(
                    cr, rules=rules, flow=flow, eval_stub=eval_stub, composite_fn=fn
                )
                oc = _outcome(comp, actual)
                arm_outcomes[arm_id].append(oc)
                row[f"{arm_id}_direction"] = comp
                row[f"{arm_id}_outcome"] = oc
                row[f"{arm_id}_active"] = active
                if arm_id == "composite_bear_conditional":
                    row["flow_gate_mode"] = meta.get("flow_gate_mode")
            day_rows.append(row)

    summary: dict[str, Any] = {}
    for r in day_rows:
        r["active_outcome"] = _outcome(
            str(r.get("composite_bear_conditional_active") or "neutral"), str(r["actual_direction"])
        )

    for arm_id, outcomes in arm_outcomes.items():
        summary[arm_id] = _metrics(
            [{"outcome": o} for o in outcomes],
            "outcome",
        )

    active_m = _metrics([{"outcome": r["active_outcome"]} for r in day_rows], "outcome")
    bear_soft = float((summary.get("composite_bear_conditional") or {}).get("soft_hit_rate") or 0)
    hold_soft = float((summary.get("composite_active_hold") or {}).get("soft_hit_rate") or 0)
    active_soft = float(active_m.get("soft_hit_rate") or 0)

    gate_rows = [{"flow_gate_mode": r.get("flow_gate_mode"), "blocks": ""} for r in day_rows]

    return {
        "schema": "kospi_composite_fallback_ab_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_months": year_months,
        "as_of_kst": as_of_kst,
        "n_scored_days": len(day_rows),
        "summary": {"active_locked": active_m, **summary},
        "soft_delta_vs_active": {
            "composite_bear_conditional": round(bear_soft - active_soft, 4),
            "composite_active_hold": round(hold_soft - active_soft, 4),
        },
        "recommendation_ko": (
            "bear_conditional=CPCV 승인 shadow; active_hold=forward fallback A/B — long-horizon bear 편향 완화 후보"
        ),
        "flow_gate_summary": summarize_flow_gate_usage(
            [{"flow_gate_mode": r.get("flow_gate_mode"), "blocks": ""} for r in day_rows]
        ),
        "rows": day_rows[:120],
        "rows_truncated": len(day_rows) > 120,
        "reproduce": (
            f"py scripts/build_kospi_composite_fallback_ab_v1.py --as-of-kst {as_of_kst} "
            + " ".join(f"--year-month {m}" for m in year_months)
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", action="append", dest="year_months")
    ap.add_argument("--as-of-kst", default="2026-06-26")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()
    months = list(dict.fromkeys(ns.year_months or ["2026-06"]))
    rules = _read(DEFAULT_RULES)
    flow = load_flow_daily(ROOT / "research/market_data/kospi_daily_flow_external.csv")
    doc = build_ab(year_months=months, as_of_kst=ns.as_of_kst, rules=rules, flow=flow)
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_composite_fallback_ab_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": doc["n_scored_days"],
                "delta_bear": doc["soft_delta_vs_active"]["composite_bear_conditional"],
                "delta_hold": doc["soft_delta_vs_active"]["composite_active_hold"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
