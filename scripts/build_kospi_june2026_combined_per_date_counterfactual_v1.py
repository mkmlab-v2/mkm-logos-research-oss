#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI combined per-date counterfactual PoC [HYPO][research_only].

Multi-arm replay on sealed calendar:
  - per_date_lens (myeongni/sasang JSONL)
  - macro_backfill (OHLCV gate only)
  - macro_tier2 (backfill + operational log priority)
  - combined_lens_macro_tier2 (lens JSONL + macro tier2)

Does not mutate active calendar or evolution weights.
"""

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

from scripts.build_kospi_june2026_channel_input_audit_v1 import (  # noqa: E402
    _momentum_from_row,
    _read_json,
    _rel,
    _resolve_calendar_path,
    _soft_from_outcomes,
)
from scripts.build_kospi_june2026_macro_daily_refresh_poc_v1 import (  # noqa: E402
    _month_end,
    ensure_macro_backfill_jsonl,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    DEFAULT_MACRO_BACKFILL_JSONL,
    load_lens_jsonl_by_day,
    load_macro_gate_by_day,
    static_lenses_for_eval_date,
)
from scripts.run_three_lens_horizon_empirical_eval_v2 import (  # noqa: E402
    _decision_to_direction,
    _gate_asof,
)

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_combined_per_date_counterfactual_latest.json"
DEFAULT_COUNTER_CAL = ROOT / "reports/kospi_202606_combined_per_date_counterfactual_calendar_v1.json"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_OPERATIONAL_JSONL = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_v1.jsonl"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"

ARM_IDS = (
    "active",
    "per_date_lens",
    "macro_backfill",
    "macro_tier2",
    "combined_lens_macro_tier2",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _replay_row(
    row: dict[str, Any],
    *,
    static_lenses: dict[str, Any],
    ensemble_by_date: dict[str, dict[str, Any]],
    weights: dict[str, float],
    neutral_band: float,
    blend_policy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    dk = str(row.get("session_date"))
    pred, score, detail = blend_v2_multilens(
        session_map=str(row.get("session_mapping_target") or "sideways"),
        session_score=float(row.get("session_direction_score") or 0.0),
        momentum_dir=_momentum_from_row(row),
        static_lenses=static_lenses,
        ensemble_row=ensemble_by_date.get(dk),
        weights=weights,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    return pred, {"blended_score": score, **detail}


def _macro_direction_asof(gate_by_day: dict[str, dict[str, Any]], eval_date: str) -> str | None:
    gate_row = _gate_asof(gate_by_day, eval_date)
    if not gate_row:
        return None
    return _decision_to_direction(
        str(gate_row.get("decision_state") or ""),
        str(gate_row.get("risk_warning_level") or ""),
    )


def build_combined_counterfactual(
    *,
    calendar: dict[str, Any],
    rules: dict[str, Any],
    eval_doc: dict[str, Any] | None,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    macro_backfill_jsonl: Path,
    operational_jsonl: Path | None,
    calendar_path: Path,
    macro_jsonl_meta: dict[str, Any],
    write_counter_calendar: bool,
    counter_calendar_path: Path,
) -> dict[str, Any]:
    rows = calendar.get("rows") if isinstance(calendar.get("rows"), list) else []
    trading_days = [str(r.get("session_date")) for r in rows if r.get("session_date")]
    weights = calendar.get("blend_weights_applied") if isinstance(calendar.get("blend_weights_applied"), dict) else {}
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}

    static_global = load_static_lenses()
    ensemble_by_date = load_ensemble_kospi_per_date(trading_days)

    jsonl_ok = myeongni_jsonl.is_file() and sasang_jsonl.is_file()
    my_by, sa_by, jsonl_meta = ({}, {}, {"available": False})
    if jsonl_ok:
        my_by, sa_by, jsonl_meta = load_lens_jsonl_by_day(myeongni_jsonl, sasang_jsonl)
        jsonl_meta["available"] = True

    gate_backfill = load_macro_gate_by_day(macro_backfill_jsonl)
    gate_tier2 = load_macro_gate_by_day(
        macro_backfill_jsonl,
        operational_jsonl=operational_jsonl if operational_jsonl and operational_jsonl.is_file() else None,
    )
    ops_available = bool(operational_jsonl and operational_jsonl.is_file())

    static_builders: dict[str, Callable[[str], dict[str, Any]]] = {
        "per_date_lens": lambda dk: static_lenses_for_eval_date(
            dk, sasang_by_day=sa_by, myeongni_by_day=my_by, baseline=static_global
        ),
        "macro_backfill": lambda dk: static_lenses_for_eval_date(
            dk, sasang_by_day={}, myeongni_by_day={}, baseline=static_global, macro_gate_by_day=gate_backfill
        ),
        "macro_tier2": lambda dk: static_lenses_for_eval_date(
            dk, sasang_by_day={}, myeongni_by_day={}, baseline=static_global, macro_gate_by_day=gate_tier2
        ),
        "combined_lens_macro_tier2": lambda dk: static_lenses_for_eval_date(
            dk,
            sasang_by_day=sa_by,
            myeongni_by_day=my_by,
            baseline=static_global,
            macro_gate_by_day=gate_tier2,
        ),
    }

    arm_directions: dict[str, dict[str, str]] = {arm: {} for arm in ARM_IDS if arm != "active"}
    arm_counts: dict[str, dict[str, int]] = {arm: {"bull": 0, "bear": 0, "neutral": 0} for arm in ARM_IDS}
    active_diffs: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARM_IDS if arm != "active"}
    counter_rows: list[dict[str, Any]] = []

    macro_tier2_vs_backfill: list[dict[str, Any]] = []
    for dk in trading_days:
        bf = _macro_direction_asof(gate_backfill, dk)
        t2 = _macro_direction_asof(gate_tier2, dk)
        if bf != t2:
            gate_bf = _gate_asof(gate_backfill, dk) or {}
            gate_t2 = _gate_asof(gate_tier2, dk) or {}
            macro_tier2_vs_backfill.append(
                {
                    "session_date": dk,
                    "backfill_direction": bf,
                    "tier2_direction": t2,
                    "backfill_source": gate_bf.get("source_label") or gate_bf.get("schema"),
                    "tier2_source": gate_t2.get("source_label") or gate_t2.get("schema"),
                }
            )

    for row in rows:
        dk = str(row.get("session_date"))
        active_dir = str(row.get("predicted_direction") or "neutral")
        arm_counts["active"][active_dir] = arm_counts["active"].get(active_dir, 0) + 1

        combined_dir = active_dir
        combined_detail: dict[str, Any] = {}

        for arm_id, builder in static_builders.items():
            if arm_id == "per_date_lens" and not jsonl_ok:
                arm_dir = active_dir
            elif arm_id.startswith("macro") and not gate_backfill:
                arm_dir = active_dir
            elif arm_id == "combined_lens_macro_tier2" and (not jsonl_ok or not gate_tier2):
                arm_dir = active_dir
            else:
                arm_dir, detail = _replay_row(
                    row,
                    static_lenses=builder(dk),
                    ensemble_by_date=ensemble_by_date,
                    weights=weights,
                    neutral_band=neutral_band,
                    blend_policy=blend_policy,
                )
                if arm_id == "combined_lens_macro_tier2":
                    combined_dir = arm_dir
                    combined_detail = detail

            arm_directions[arm_id][dk] = arm_dir
            arm_counts[arm_id][arm_dir] = arm_counts[arm_id].get(arm_dir, 0) + 1
            if arm_dir != active_dir:
                active_diffs[arm_id].append(
                    {
                        "session_date": dk,
                        "active_direction": active_dir,
                        "arm_direction": arm_dir,
                        "arm_id": arm_id,
                    }
                )

        counter_rows.append(
            {
                **row,
                "predicted_direction": combined_dir,
                "predicted_direction_ko": {"bull": "상승", "bear": "하락", "neutral": "횡보·관측"}.get(
                    combined_dir, combined_dir
                ),
                "counterfactual_meta": {
                    "kind": "combined_lens_macro_tier2",
                    "active_direction": active_dir,
                    "changed_vs_active": combined_dir != active_dir,
                },
                "blend": combined_detail if combined_detail else row.get("blend"),
            }
        )

    scored_by_arm: dict[str, list[str]] = {arm: [] for arm in ARM_IDS}
    scored_days: list[dict[str, Any]] = []
    for er in (eval_doc or {}).get("rows") or []:
        dk = str(er.get("session_date"))
        actual = str(er.get("actual_direction") or "neutral")
        active_dir = str(er.get("predicted_direction") or "neutral")
        day_rec: dict[str, Any] = {"session_date": dk, "actual_direction": actual, "arms": {}}
        for arm_id in ARM_IDS:
            if arm_id == "active":
                direction = active_dir
            else:
                direction = arm_directions.get(arm_id, {}).get(dk, active_dir)
            oc = _outcome(direction, actual)
            scored_by_arm[arm_id].append(oc)
            day_rec["arms"][arm_id] = {"direction": direction, "outcome": oc}
        scored_days.append(day_rec)

    soft_by_arm = {arm: _soft_from_outcomes(outcomes) for arm, outcomes in scored_by_arm.items()}
    n_scored = len(scored_days)

    counter_calendar_doc: dict[str, Any] | None = None
    if write_counter_calendar and jsonl_ok and gate_tier2:
        counter_calendar_doc = {
            **{k: v for k, v in calendar.items() if k != "rows"},
            "schema": "kospi_monthly_daily_prophecy_calendar_v2_counterfactual",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "auto_apply": False,
            "counterfactual_kind": "combined_lens_macro_tier2",
            "active_calendar_path": _rel(calendar_path),
            "note_ko": "combined PoC — active calendar·evolution apply 금지",
            "rows": counter_rows,
        }
        counter_calendar_path.parent.mkdir(parents=True, exist_ok=True)
        counter_calendar_path.write_text(
            json.dumps(counter_calendar_doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    findings: list[str] = []
    findings.append(
        f"macro tier2 vs backfill macro direction diff {len(macro_tier2_vs_backfill)}/{len(trading_days)} "
        f"(ops log={'yes' if ops_available else 'no'})"
    )
    for arm_id in ("per_date_lens", "macro_tier2", "combined_lens_macro_tier2"):
        n_diff = len(active_diffs.get(arm_id) or [])
        findings.append(
            f"{arm_id}: 방향 diff vs active {n_diff}/{len(rows)} · "
            f"neutral {arm_counts['active'].get('neutral', 0)}→{arm_counts[arm_id].get('neutral', 0)}"
        )
    if n_scored:
        active_soft = soft_by_arm.get("active")
        comb_soft = soft_by_arm.get("combined_lens_macro_tier2")
        findings.append(
            f"scored soft active={active_soft} · lens={soft_by_arm.get('per_date_lens')} · "
            f"macro_tier2={soft_by_arm.get('macro_tier2')} · combined={comb_soft} (n={n_scored})"
        )

    return {
        "schema": "kospi_june2026_combined_per_date_counterfactual_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": calendar.get("year_month") or "2026-06",
        "active_calendar_path": _rel(calendar_path),
        "counter_calendar_path": _rel(counter_calendar_path) if counter_calendar_doc else None,
        "per_date_jsonl": jsonl_meta,
        "macro_jsonl": macro_jsonl_meta,
        "operational_macro_jsonl": {
            "path": _rel(operational_jsonl) if ops_available and operational_jsonl else None,
            "available": ops_available,
        },
        "macro_tier2_vs_backfill": macro_tier2_vs_backfill,
        "arms": {
            arm_id: {
                "direction_counts": arm_counts[arm_id],
                "n_direction_diffs_vs_active": len(active_diffs.get(arm_id) or []),
                "direction_diffs_vs_active": active_diffs.get(arm_id) or [],
                "scored_soft_hit_rate": soft_by_arm.get(arm_id),
            }
            for arm_id in ARM_IDS
        },
        "scored_forward": {
            "n_scored": n_scored,
            "soft_by_arm": soft_by_arm,
            "days": scored_days,
        },
        "key_findings_ko": findings,
        "recommended_next_ko": "n≥7 scored 후 combined soft 추적; evolution dry-run only if uplift persists. apply 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--macro-jsonl", type=Path, default=DEFAULT_MACRO_BACKFILL_JSONL)
    ap.add_argument("--operational-jsonl", type=Path, default=DEFAULT_OPERATIONAL_JSONL)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--refresh-macro-backfill", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-counter-calendar", action="store_true", default=True)
    ap.add_argument("--no-write-counter-calendar", action="store_false", dest="write_counter_calendar")
    ap.add_argument("--counter-calendar-json", type=Path, default=DEFAULT_COUNTER_CAL)
    args = ap.parse_args(argv)

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month)
    calendar = _read_json(cal_path)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {cal_path}")

    macro_meta = ensure_macro_backfill_jsonl(
        macro_jsonl=args.macro_jsonl,
        csv_path=args.kospi_csv,
        date_from="1996-01-01",
        date_to=_month_end(args.year_month),
        refresh=args.refresh_macro_backfill,
    )

    doc = build_combined_counterfactual(
        calendar=calendar,
        rules=_read_json(args.rules_json),
        eval_doc=_read_json(args.eval_json) if args.eval_json.is_file() else None,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        macro_backfill_jsonl=args.macro_jsonl,
        operational_jsonl=args.operational_jsonl,
        calendar_path=cal_path,
        macro_jsonl_meta=macro_meta,
        write_counter_calendar=args.write_counter_calendar,
        counter_calendar_path=args.counter_calendar_json,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sf = doc.get("scored_forward") or {}
    soft = sf.get("soft_by_arm") or {}
    comb = doc.get("arms", {}).get("combined_lens_macro_tier2", {})
    print(
        f"WROTE: {args.output.resolve()} combined_diffs={comb.get('n_direction_diffs_vs_active')} "
        f"scored_soft active={soft.get('active')}→combined={soft.get('combined_lens_macro_tier2')}"
    )
    if doc.get("counter_calendar_path"):
        print(f"WROTE: {(ROOT / doc['counter_calendar_path']).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
