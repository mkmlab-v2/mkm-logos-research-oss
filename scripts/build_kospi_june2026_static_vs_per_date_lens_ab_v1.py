#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static snapshot vs per-date lens replay A/B for June KOSPI [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
DEFAULT_OUT = ROOT / "reports/kospi_june2026_static_vs_per_date_lens_ab_v1_latest.json"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _replay_calendar(
    calendar: dict[str, Any],
    *,
    mode: str,
    global_static: dict[str, Any],
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    ensemble_by_date: dict[str, dict[str, Any]],
    neutral_band: float,
    blend_policy: dict[str, Any],
) -> tuple[Counter[str], list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    rows_out: list[dict[str, Any]] = []
    for row in calendar.get("rows") or []:
        dk = str(row.get("session_date") or "")
        session_map = str(row.get("session_mapping_target") or "sideways")
        session_score = float(row.get("session_direction_score") or 0.0)
        mom_dir = _momentum_from_row(row)
        blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
        weights = blend.get("weights") or {}
        if mode == "per_date":
            static = static_lenses_for_eval_date(
                dk,
                baseline=global_static,
                myeongni_by_day=myeongni_by_day,
                sasang_by_day=sasang_by_day,
            )
        else:
            static = global_static
        pred, _, _detail = blend_v2_multilens(
            session_map=session_map,
            session_score=session_score,
            momentum_dir=mom_dir,
            static_lenses=static,
            ensemble_row=ensemble_by_date.get(dk),
            weights=weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        counts[pred] += 1
        rows_out.append({"session_date": dk, "predicted_direction": pred})
    return counts, rows_out


def build_ab(
    *,
    calendar_path: Path,
    eval_path: Path,
    rules_path: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
) -> dict[str, Any]:
    calendar = _read_json(calendar_path)
    eval_doc = _read_json(eval_path)
    rules = _read_json(rules_path)
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    neutral_band = float(rules.get("neutral_band_bps") or 6) / 100.0

    global_static = load_static_lenses()
    myeongni_by_day, sasang_by_day, _jsonl_meta = load_lens_jsonl_by_day(myeongni_jsonl, sasang_jsonl)
    trading_days = [str(r.get("session_date") or "")[:10] for r in calendar.get("rows") or []]
    ensemble_by_date = load_ensemble_kospi_per_date(trading_days)

    static_counts, static_rows = _replay_calendar(
        calendar,
        mode="static",
        global_static=global_static,
        myeongni_by_day=myeongni_by_day,
        sasang_by_day=sasang_by_day,
        ensemble_by_date=ensemble_by_date,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    per_date_counts, per_date_rows = _replay_calendar(
        calendar,
        mode="per_date",
        global_static=global_static,
        myeongni_by_day=myeongni_by_day,
        sasang_by_day=sasang_by_day,
        ensemble_by_date=ensemble_by_date,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )

    static_by_date = {r["session_date"]: r["predicted_direction"] for r in static_rows}
    per_date_by_date = {r["session_date"]: r["predicted_direction"] for r in per_date_rows}
    diffs = [
        {
            "session_date": dk,
            "static": static_by_date[dk],
            "per_date": per_date_by_date[dk],
            "published": str(
                next(
                    (str(r.get("predicted_direction") or "") for r in calendar.get("rows") or [] if str(r.get("session_date")) == dk),
                    "",
                )
            ),
        }
        for dk in sorted(set(static_by_date) & set(per_date_by_date))
        if static_by_date[dk] != per_date_by_date[dk]
    ]

    scored_dates = {
        str(r.get("session_date") or "")
        for r in eval_doc.get("rows") or []
        if r.get("actual_direction")
    }
    static_outcomes: list[str] = []
    per_date_outcomes: list[str] = []
    scored_day_rows: list[dict[str, Any]] = []
    for dk in sorted(scored_dates):
        actual = str(
            next(
                (r.get("actual_direction") for r in eval_doc.get("rows") or [] if str(r.get("session_date")) == dk),
                "",
            )
        )
        if not actual:
            continue
        s_dir = static_by_date.get(dk, "neutral")
        p_dir = per_date_by_date.get(dk, "neutral")
        s_out = _outcome(s_dir, actual)
        p_out = _outcome(p_dir, actual)
        static_outcomes.append(s_out)
        per_date_outcomes.append(p_out)
        scored_day_rows.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "static_direction": s_dir,
                "static_outcome": s_out,
                "per_date_direction": p_dir,
                "per_date_outcome": p_out,
            }
        )

    published_outcomes = [
        str(r.get("outcome") or "")
        for r in eval_doc.get("rows") or []
        if r.get("actual_direction")
    ]

    return {
        "schema": "kospi_june2026_static_vs_per_date_lens_ab_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "calendar_path": _rel(calendar_path),
        "eval_path": _rel(eval_path),
        "per_date_jsonl": {
            "myeongni": _rel(myeongni_jsonl),
            "sasang": _rel(sasang_jsonl),
            "myeongni_days": len(myeongni_by_day),
            "sasang_days": len(sasang_by_day),
        },
        "full_month_replay": {
            "static_direction_counts": dict(static_counts),
            "per_date_direction_counts": dict(per_date_counts),
            "n_direction_diffs": len(diffs),
            "diff_sample": diffs[:15],
        },
        "scored_forward_ab": {
            "n_scored": len(scored_day_rows),
            "published_soft_hit_rate": _soft_from_outcomes(published_outcomes),
            "static_replay_soft_hit_rate": _soft_from_outcomes(static_outcomes),
            "per_date_replay_soft_hit_rate": _soft_from_outcomes(per_date_outcomes),
            "delta_per_date_minus_static_soft": round(
                _soft_from_outcomes(per_date_outcomes) - _soft_from_outcomes(static_outcomes),
                4,
            )
            if scored_day_rows
            else None,
            "days": scored_day_rows,
        },
        "verdict_ko": (
            "per-date JSONL replay가 static snapshot 대비 scored soft HR 개선 shadow — "
            "n<15·apply 금지. published 캘린더는 static 기준 유지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    cal = _resolve_calendar_path(args.calendar_json, year_month=args.year_month)
    doc = build_ab(
        calendar_path=cal,
        eval_path=args.eval_json,
        rules_path=args.rules_json,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sf = doc["scored_forward_ab"]
    print(
        f"WROTE: {args.output.resolve()} "
        f"n_scored={sf.get('n_scored')} "
        f"static_soft={sf.get('static_replay_soft_hit_rate')} "
        f"per_date_soft={sf.get('per_date_replay_soft_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
