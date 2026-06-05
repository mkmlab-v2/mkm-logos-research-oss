#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI per-date lens counterfactual PoC [HYPO][research_only].

Replays published calendar rows with static_lenses_for_eval_date (myeongni/sasang JSONL)
vs global snapshot. Does not mutate active calendar or evolution weights.
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

from scripts.build_kospi_june2026_channel_input_audit_v1 import (  # noqa: E402
    _momentum_from_row,
    _read_json,
    _rel,
    _resolve_calendar_path,
    _soft_from_outcomes,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    load_lens_jsonl_by_day,
    static_lenses_for_eval_date,
)

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_per_date_lens_counterfactual_latest.json"
DEFAULT_COUNTER_CAL = ROOT / "reports/kospi_202606_per_date_lens_counterfactual_calendar_v1.json"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _replay_counterfactual_row(
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


def build_counterfactual(
    *,
    calendar: dict[str, Any],
    rules: dict[str, Any],
    eval_doc: dict[str, Any] | None,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    calendar_path: Path,
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

    diffs: list[dict[str, Any]] = []
    counter_rows: list[dict[str, Any]] = []
    active_counts: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    counter_counts: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}

    for row in rows:
        dk = str(row.get("session_date"))
        active_dir = str(row.get("predicted_direction") or "neutral")
        active_counts[active_dir] = active_counts.get(active_dir, 0) + 1

        if not jsonl_ok:
            counter_dir = active_dir
            blend_detail: dict[str, Any] = {}
            lens_note = "jsonl_missing_fallback_active"
        else:
            per_static = static_lenses_for_eval_date(
                dk, sasang_by_day=sa_by, myeongni_by_day=my_by, baseline=static_global
            )
            counter_dir, blend_detail = _replay_counterfactual_row(
                row,
                static_lenses=per_static,
                ensemble_by_date=ensemble_by_date,
                weights=weights,
                neutral_band=neutral_band,
                blend_policy=blend_policy,
            )
            lens_note = "per_date_jsonl_replay"

        counter_counts[counter_dir] = counter_counts.get(counter_dir, 0) + 1
        if counter_dir != active_dir:
            diffs.append(
                {
                    "session_date": dk,
                    "active_direction": active_dir,
                    "counterfactual_direction": counter_dir,
                    "session_mapping_target": row.get("session_mapping_target"),
                    "counter_votes": blend_detail.get("votes"),
                    "counter_resolution": blend_detail.get("winner_resolution"),
                    "sasang_per_date": (per_static.get("sasang") if jsonl_ok else {}),
                    "myeongni_per_date": (per_static.get("myeongni_independent") if jsonl_ok else {}),
                }
            )

        counter_rows.append(
            {
                **row,
                "predicted_direction": counter_dir,
                "predicted_direction_ko": {"bull": "상승", "bear": "하락", "neutral": "횡보·관측"}.get(
                    counter_dir, counter_dir
                ),
                "counterfactual_meta": {
                    "source": lens_note,
                    "active_direction": active_dir,
                    "changed_vs_active": counter_dir != active_dir,
                },
                "blend": blend_detail if jsonl_ok else row.get("blend"),
            }
        )

    scored_eval: list[dict[str, Any]] = []
    active_outcomes: list[str] = []
    counter_outcomes: list[str] = []
    for er in (eval_doc or {}).get("rows") or []:
        dk = str(er.get("session_date"))
        actual = str(er.get("actual_direction") or "neutral")
        active_dir = str(er.get("predicted_direction") or "neutral")
        active_oc = str(er.get("outcome") or _outcome(active_dir, actual))
        active_outcomes.append(active_oc)

        counter_row = next((r for r in counter_rows if str(r.get("session_date")) == dk), None)
        counter_dir = str((counter_row or {}).get("predicted_direction") or active_dir)
        counter_oc = _outcome(counter_dir, actual)
        counter_outcomes.append(counter_oc)
        scored_eval.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "active_direction": active_dir,
                "active_outcome": active_oc,
                "counterfactual_direction": counter_dir,
                "counterfactual_outcome": counter_oc,
            }
        )

    counter_calendar_doc: dict[str, Any] | None = None
    if write_counter_calendar and jsonl_ok:
        counter_calendar_doc = {
            **{k: v for k, v in calendar.items() if k != "rows"},
            "schema": "kospi_monthly_daily_prophecy_calendar_v2_counterfactual",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "auto_apply": False,
            "counterfactual_kind": "per_date_myeongni_sasang_jsonl",
            "active_calendar_path": _rel(calendar_path),
            "note_ko": "연구 PoC — active calendar 대체·evolution apply 금지",
            "rows": counter_rows,
        }
        counter_calendar_path.parent.mkdir(parents=True, exist_ok=True)
        counter_calendar_path.write_text(
            json.dumps(counter_calendar_doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    findings: list[str] = []
    if not jsonl_ok:
        findings.append("per-date JSONL 없음 — counterfactual PoC skip")
    else:
        findings.append(
            f"June 방향 diff {len(diffs)}/{len(rows)} — "
            f"active neutral={active_counts.get('neutral', 0)} → "
            f"counter neutral={counter_counts.get('neutral', 0)}"
        )
        if scored_eval:
            a_soft = _soft_from_outcomes(active_outcomes)
            c_soft = _soft_from_outcomes(counter_outcomes)
            if a_soft is not None and c_soft is not None and c_soft != a_soft:
                findings.append(
                    f"scored soft {a_soft} → {c_soft} (n={len(scored_eval)}) — research_only, apply 금지"
                )
            elif scored_eval:
                findings.append(f"scored soft unchanged at {_soft_from_outcomes(active_outcomes)} (n={len(scored_eval)})")

    return {
        "schema": "kospi_june2026_per_date_lens_counterfactual_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": calendar.get("year_month") or "2026-06",
        "active_calendar_path": _rel(calendar_path),
        "counter_calendar_path": _rel(counter_calendar_path) if counter_calendar_doc else None,
        "per_date_jsonl": jsonl_meta,
        "direction_diffs": diffs,
        "summary": {
            "n_trading_days": len(rows),
            "n_direction_diffs": len(diffs),
            "active_direction_counts": active_counts,
            "counterfactual_direction_counts": counter_counts,
            "scored_forward": {
                "n_scored": len(scored_eval),
                "active_soft_hit_rate": _soft_from_outcomes(active_outcomes),
                "counterfactual_soft_hit_rate": _soft_from_outcomes(counter_outcomes),
                "days": scored_eval,
            },
        },
        "key_findings_ko": findings,
        "recommended_next_ko": "n≥15 포워드 후 counterfactual soft 재평가; macro 일별 갱신 PoC 별도. apply 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-counter-calendar", action="store_true", default=True)
    ap.add_argument("--no-write-counter-calendar", action="store_false", dest="write_counter_calendar")
    ap.add_argument("--counter-calendar-json", type=Path, default=DEFAULT_COUNTER_CAL)
    args = ap.parse_args(argv)

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month)
    calendar = _read_json(cal_path)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {cal_path}")

    doc = build_counterfactual(
        calendar=calendar,
        rules=_read_json(args.rules_json),
        eval_doc=_read_json(args.eval_json) if args.eval_json.is_file() else None,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        calendar_path=cal_path,
        write_counter_calendar=args.write_counter_calendar,
        counter_calendar_path=args.counter_calendar_json,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summ = doc["summary"]
    sf = summ.get("scored_forward") or {}
    print(
        f"WROTE: {args.output.resolve()} diffs={summ.get('n_direction_diffs')} "
        f"scored_soft {sf.get('active_soft_hit_rate')}→{sf.get('counterfactual_soft_hit_rate')}"
    )
    if doc.get("counter_calendar_path"):
        print(f"WROTE: {(ROOT / doc['counter_calendar_path']).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
