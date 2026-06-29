#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Direction rule shadow panel: weight rules + shock_gate reference [HYPO][research_only]."""

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

from scripts.kospi_hero_shock_gate_shadow_lib_v1 import (  # noqa: E402
    aggregate_shadow_days,
    resolve_policy,
    score_shadow_day,
)
from scripts.kospi_weight_counterfactual_lib_v1 import (  # noqa: E402
    scenario_ids_for_panel,
    score_weight_rule_month,
)

EVOLUTION = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_direction_rule_shadow_panel_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_direction_rule_shadow_panel_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paths_for_month(year_month: str) -> tuple[Path, Path, Path]:
    tag = year_month.replace("-", "")
    ev = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    if year_month == "2026-06" and not ev.is_file():
        ev = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    cal = ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    out = ROOT / f"reports/kospi_{tag}_direction_rule_shadow_panel_v1_latest.json"
    return cal, ev, out


def build_panel(
    *,
    calendar: dict[str, Any],
    kospi_eval: dict[str, Any],
    hero_cal: dict[str, Any],
    rules: dict[str, Any],
    as_of_kst: str | None = None,
    year_month: str | None = None,
) -> dict[str, Any]:
    pol = rules.get("direction_rule_shadow_policy")
    pol = pol if isinstance(pol, dict) else {}
    weight_ids = scenario_ids_for_panel(pol)

    weight_rules = [
        score_weight_rule_month(
            calendar=calendar,
            eval_doc=kospi_eval,
            scenario_id=sid,
            rules=rules,
            as_of_kst=as_of_kst,
        )
        for sid in weight_ids
    ]

    shock_policy = resolve_policy(rules)
    hero_by = {
        str(r.get("session_date") or "")[:10]: r
        for r in (hero_cal.get("rows") or [])
        if isinstance(r, dict) and r.get("session_date")
    }
    eval_rows = [r for r in (kospi_eval.get("rows") or []) if isinstance(r, dict)]
    if as_of_kst:
        eval_rows = [r for r in eval_rows if str(r.get("session_date") or "") <= as_of_kst[:10]]

    shock_days: list[dict[str, Any]] = []
    for er in eval_rows:
        dk = str(er.get("session_date") or "")[:10]
        hero_row = hero_by.get(dk) or {}
        shock_days.append(
            score_shadow_day(
                session_date=dk,
                active_direction=str(er.get("predicted_direction") or "neutral"),
                actual_direction=str(er.get("actual_direction") or "neutral"),
                shock_pred=((hero_row.get("slots") or {}).get("macro_news_shock") or {}),
                foreign_flow_pred=((hero_row.get("slots") or {}).get("foreign_flow") or {}),
                policy=shock_policy,
            )
        )
    shock_agg = aggregate_shadow_days(shock_days)

    ym = year_month or kospi_eval.get("year_month") or calendar.get("year_month")
    oos_start = str(pol.get("oos_forward_start") or shock_policy.get("oos_forward_start") or "2026-07-01")

    return {
        "schema": "kospi_direction_rule_shadow_panel_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": ym,
        "as_of_kst": as_of_kst,
        "policy": pol,
        "weight_rules": weight_rules,
        "hero_shock_gate": {
            "rule_id": "hero_shock_gate_v2",
            "type": "rule_override",
            "aggregate": shock_agg,
            "policy": shock_policy,
        },
        "oos_forward_start": oos_start,
        "verdict_ko": (
            "weight·shock rule shadow — apply·Track A 금지. "
            + "; ".join(
                f"{w['rule_id']} Δsoft {w.get('rule_minus_active_soft_pp')}pp"
                for w in weight_rules
            )
            + f"; shock_gate Δsoft {shock_agg.get('shadow_minus_active_soft_pp')}pp"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--rules-json", type=Path, default=EVOLUTION)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    args = ap.parse_args()

    ym = args.year_month
    out_p = args.output if args.output.is_absolute() else ROOT / args.output
    cal_p = ev_p = None
    if ym:
        cal_p, ev_p, month_out = _paths_for_month(ym)
        if args.output == DEFAULT_OUT:
            out_p = month_out

    cal_p = cal_p or ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
    ev_p = ev_p or ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    hero_p = ROOT / "reports/btrack_daily_hero_board_calendar_v1_latest.json"
    rules = _read_json(args.rules_json if args.rules_json.is_absolute() else ROOT / args.rules_json)

    doc = build_panel(
        calendar=_read_json(cal_p),
        kospi_eval=_read_json(ev_p),
        hero_cal=_read_json(hero_p),
        rules=rules,
        as_of_kst=args.as_of_kst,
        year_month=ym,
    )
    doc["inputs"] = {
        "calendar_path": str(cal_p).replace("\\", "/"),
        "eval_path": str(ev_p).replace("\\", "/"),
        "hero_calendar_path": str(hero_p).replace("\\", "/"),
    }

    art_p = args.artifact if args.artifact.is_absolute() else ROOT / args.artifact
    for p in (out_p, art_p, DEFAULT_OUT):
        if p == DEFAULT_OUT and out_p != DEFAULT_OUT and ym and ym != "2026-06":
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_p),
                "weight_rules": [w["rule_id"] for w in doc.get("weight_rules") or []],
                "shock_delta_soft_pp": (doc.get("hero_shock_gate") or {}).get("aggregate", {}).get(
                    "shadow_minus_active_soft_pp"
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
