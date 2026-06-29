#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-date lenses + weight counterfactual shadow panel [HYPO][research_only].

Combines P0 per_date myeongni/sasang JSONL with weight scenarios (bear_triple etc).
Does NOT mutate active calendar or evolution weights.
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

from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    load_lens_jsonl_by_day,
)
from scripts.kospi_weight_counterfactual_lib_v1 import (  # noqa: E402
    ACTIVE_WEIGHTS,
    scenario_ids_for_panel,
    score_weight_rule_month,
    score_weight_rule_month_per_date,
)

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_per_date_weight_counterfactual_shadow_v1_latest.json"


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
    out = ROOT / f"reports/kospi_{tag}_per_date_weight_counterfactual_shadow_v1_latest.json"
    return cal, ev, out


def build_shadow_panel(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    as_of_kst: str,
    year_month: str,
) -> dict[str, Any]:
    pol = rules.get("direction_rule_shadow_policy")
    pol = pol if isinstance(pol, dict) else {}
    scenario_ids = scenario_ids_for_panel(pol)

    static_rules = [
        score_weight_rule_month(
            calendar=calendar,
            eval_doc=eval_doc,
            scenario_id=sid,
            rules=rules,
            as_of_kst=as_of_kst,
        )
        for sid in scenario_ids
    ]
    per_date_rules = [
        score_weight_rule_month_per_date(
            calendar=calendar,
            eval_doc=eval_doc,
            scenario_id=sid,
            rules=rules,
            myeongni_by_day=myeongni_by_day,
            sasang_by_day=sasang_by_day,
            as_of_kst=as_of_kst,
        )
        for sid in scenario_ids
    ]

    baseline_per_date = score_weight_rule_month_per_date(
        calendar=calendar,
        eval_doc=eval_doc,
        scenario_id="active_v2_lens3_heavy",
        rules=rules,
        myeongni_by_day=myeongni_by_day,
        sasang_by_day=sasang_by_day,
        as_of_kst=as_of_kst,
    )

    fail_rescues: dict[str, int] = {}
    for row in per_date_rules:
        fail_rescues[str(row.get("rule_id"))] = int(row.get("n_rescued_active_fail") or 0)

    n_scored = int(baseline_per_date.get("n_scored") or 0)
    baseline_soft = (baseline_per_date.get("rule") or {}).get("soft_hit_rate")
    active_soft = (baseline_per_date.get("active") or {}).get("soft_hit_rate")

    for static_row, pd_row in zip(static_rules, per_date_rules):
        pd_soft = (pd_row.get("rule") or {}).get("soft_hit_rate")
        st_soft = (static_row.get("rule") or {}).get("soft_hit_rate")
        pd_row["static_lens_same_weights_soft"] = st_soft
        pd_row["per_date_minus_static_same_weights_pp"] = (
            round(float(pd_soft) - float(st_soft), 4) if pd_soft is not None and st_soft is not None else None
        )
        if str(pd_row.get("rule_id")) != "active_v2_lens3_heavy":
            pd_row["rule_minus_per_date_baseline_soft_pp"] = (
                round(float(pd_soft) - float(baseline_soft), 4)
                if pd_soft is not None and baseline_soft is not None
                else None
            )

    leader = None
    best_delta = None
    for row in per_date_rules:
        if str(row.get("rule_id")) == "active_v2_lens3_heavy":
            continue
        delta = row.get("rule_minus_per_date_baseline_soft_pp")
        if delta is None or float(delta) <= 0:
            continue
        if best_delta is None or float(delta) > float(best_delta):
            best_delta = float(delta)
            leader = row.get("rule_id")

    return {
        "schema": "kospi_per_date_weight_counterfactual_shadow_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "production_apply_authorized": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "n_scored": n_scored,
        "baseline": {
            "active_static_calendar_soft": active_soft,
            "per_date_active_weights_soft": baseline_soft,
            "per_date_minus_active_static_pp": round(float(baseline_soft) - float(active_soft), 4)
            if baseline_soft is not None and active_soft is not None
            else None,
            "weights": dict(ACTIVE_WEIGHTS),
        },
        "static_lens_weight_rules": static_rules,
        "per_date_lens_weight_rules": per_date_rules,
        "leader_per_date_rule": leader,
        "leader_per_date_delta_pp": best_delta,
        "per_date_fail_rescues": fail_rescues,
        "headline_ko": (
            f"{year_month} n={n_scored} per_date baseline soft {baseline_soft} "
            f"vs leader {leader} Δ {best_delta}pp (shadow) — apply HOLD"
            if n_scored and leader is not None
            else (
                f"{year_month} n={n_scored} per_date baseline {baseline_soft} — "
                f"weight scenarios no uplift vs per_date active weights (shadow HOLD)"
                if n_scored
                else f"{year_month} n_scored={n_scored} — per_date weight shadow pending"
            )
        ),
        "reproduce": (
            f"py scripts/build_kospi_per_date_weight_counterfactual_shadow_v1.py "
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
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
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

    calendar = _read(cal_p)
    eval_doc = _read(ev_p)
    rules = _read(ns.rules_json if ns.rules_json.is_absolute() else ROOT / ns.rules_json)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {cal_p}")

    my_by, sa_by, jsonl_meta = load_lens_jsonl_by_day(ns.myeongni_jsonl, ns.sasang_jsonl)
    if not my_by or not sa_by:
        raise SystemExit("per_date JSONL missing — cannot build shadow panel")

    doc = build_shadow_panel(
        calendar=calendar,
        eval_doc=eval_doc,
        rules=rules,
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        as_of_kst=ns.as_of_kst,
        year_month=ns.year_month,
    )
    doc["per_date_jsonl"] = jsonl_meta

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_per_date_weight_counterfactual_shadow_v1_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": doc["n_scored"],
                "per_date_baseline_soft": doc["baseline"].get("per_date_active_weights_soft"),
                "leader": doc.get("leader_per_date_rule"),
                "leader_delta_pp": doc.get("leader_per_date_delta_pp"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
