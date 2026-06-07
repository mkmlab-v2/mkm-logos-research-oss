#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI Logos per-date lens PoC — global snapshot vs macro-gate-asof [HYPO]."""

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
    DEFAULT_MACRO_BACKFILL_JSONL,
    load_macro_gate_by_day,
    static_lenses_for_eval_date,
    load_lens_jsonl_by_day,
)
from scripts.kospi_logos_per_date_lens_poc_v1 import logos_lens_for_eval_date  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_logos_per_date_lens_poc_v1_latest.json"
DEFAULT_JSONL = ROOT / "reports/kospi_logos_per_date_lens_poc_v1.jsonl"
DEFAULT_MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lenses_for_mode(
    mode: str,
    eval_date: str,
    *,
    global_static: dict[str, Any],
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    macro_gate_by_day: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if mode == "global_logos":
        return global_static
    base = static_lenses_for_eval_date(
        eval_date,
        baseline=global_static,
        myeongni_by_day=myeongni_by_day,
        sasang_by_day=sasang_by_day,
        macro_gate_by_day=macro_gate_by_day,
    )
    if mode == "per_date_logos_macro_gate":
        return logos_lens_for_eval_date(
            eval_date,
            baseline=base,
            macro_gate_by_day=macro_gate_by_day,
        )
    raise ValueError(f"unknown mode: {mode}")


def build_poc(
    *,
    calendar_path: Path,
    eval_path: Path,
    rules_path: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    macro_jsonl: Path,
) -> dict[str, Any]:
    calendar = _read_json(calendar_path)
    eval_doc = _read_json(eval_path)
    rules = _read_json(rules_path)
    global_static = load_static_lenses()
    my_by, sa_by, jsonl_meta = load_lens_jsonl_by_day(myeongni_jsonl, sasang_jsonl)
    macro_gate_by_day = load_macro_gate_by_day(macro_jsonl)
    cal_rows = [r for r in (calendar.get("rows") or []) if isinstance(r, dict)]
    eval_dates = [str(r.get("session_date") or "")[:10] for r in cal_rows if r.get("session_date")]
    ensemble_by_date = load_ensemble_kospi_per_date(eval_dates)
    neutral_band = float(rules.get("neutral_band") or 0.15)
    blend_policy = rules.get("blend_policy") if isinstance(rules.get("blend_policy"), dict) else {}

    eval_by_date = {
        str(r.get("session_date") or "")[:10]: r
        for r in (eval_doc.get("rows") or [])
        if isinstance(r, dict)
    }

    jsonl_rows: list[dict[str, Any]] = []
    direction_diffs = 0
    logos_diffs = 0
    scored: dict[str, list[str]] = {"global_logos": [], "per_date_logos_macro_gate": []}

    for row in cal_rows:
        dk = str(row.get("session_date") or "")[:10]
        session_map = str(row.get("session_mapping_target") or "sideways")
        session_score = float(row.get("session_direction_score") or 0.0)
        mom_dir = _momentum_from_row(row)
        blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
        weights = blend.get("weights") or {}

        global_lens = _lenses_for_mode(
            "global_logos",
            dk,
            global_static=global_static,
            myeongni_by_day=my_by,
            sasang_by_day=sa_by,
            macro_gate_by_day=macro_gate_by_day,
        )
        pd_lens = _lenses_for_mode(
            "per_date_logos_macro_gate",
            dk,
            global_static=global_static,
            myeongni_by_day=my_by,
            sasang_by_day=sa_by,
            macro_gate_by_day=macro_gate_by_day,
        )

        g_pred, _, _ = blend_v2_multilens(
            session_map=session_map,
            session_score=session_score,
            momentum_dir=mom_dir,
            static_lenses=global_lens,
            ensemble_row=ensemble_by_date.get(dk),
            weights=weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        p_pred, _, _ = blend_v2_multilens(
            session_map=session_map,
            session_score=session_score,
            momentum_dir=mom_dir,
            static_lenses=pd_lens,
            ensemble_row=ensemble_by_date.get(dk),
            weights=weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        if g_pred != p_pred:
            direction_diffs += 1
        g_logos = str((global_lens.get("logos") or {}).get("direction") or "neutral")
        p_logos = str((pd_lens.get("logos") or {}).get("direction") or "neutral")
        if g_logos != p_logos:
            logos_diffs += 1

        jsonl_rows.append(
            {
                "schema": "kospi_logos_per_date_lens_poc_v1",
                "session_date": dk,
                "hypothesis_tier": "B",
                "research_only": True,
                "logos_global_direction": g_logos,
                "logos_per_date_direction": p_logos,
                "logos_per_date_meta": pd_lens.get("logos"),
                "blend_global_logos": g_pred,
                "blend_per_date_logos": p_pred,
            }
        )

        er = eval_by_date.get(dk)
        if not er:
            continue
        actual = str(er.get("actual_direction") or "")
        for mode_key, pred in (
            ("global_logos", g_pred),
            ("per_date_logos_macro_gate", p_pred),
        ):
            oc = _outcome(pred, actual)
            scored[mode_key].append(oc)

    soft_global = _soft_from_outcomes(scored["global_logos"]) if scored["global_logos"] else None
    soft_pd = _soft_from_outcomes(scored["per_date_logos_macro_gate"]) if scored["per_date_logos_macro_gate"] else None

    return {
        "schema": "kospi_logos_per_date_lens_poc_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": {
            "non_gating_logos_only": True,
            "a_track_auto_promotion": False,
            "equal_weight_logos_blend": False,
        },
        "calendar_path": _rel(calendar_path),
        "eval_path": _rel(eval_path),
        "macro_jsonl": _rel(macro_jsonl),
        "per_date_jsonl_meta": jsonl_meta,
        "macro_gate_days": len(macro_gate_by_day),
        "full_month": {
            "n_calendar_rows": len(jsonl_rows),
            "blend_direction_diffs": direction_diffs,
            "logos_direction_diffs": logos_diffs,
        },
        "scored_forward_ab": {
            "n_scored": len(scored["global_logos"]),
            "global_logos_soft_hit_rate": soft_global,
            "per_date_logos_macro_gate_soft_hit_rate": soft_pd,
            "delta_per_date_minus_global_soft": (
                round(float(soft_pd) - float(soft_global), 4)
                if soft_global is not None and soft_pd is not None
                else None
            ),
        },
        "verdict_ko": (
            "per-date Logos(macro-gate proxy) shadow PoC — apply·Track A·equal-weight 승격 금지. "
            "field/logos RAG per-date는 미구현."
        ),
        "_jsonl_rows": jsonl_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KOSPI Logos per-date lens PoC report.")
    ap.add_argument("--calendar", type=Path, default=None)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--macro-jsonl", type=Path, default=DEFAULT_MACRO_BACKFILL_JSONL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_JSONL)
    args = ap.parse_args()

    cal = args.calendar or _resolve_calendar_path(None)
    doc = build_poc(
        calendar_path=cal,
        eval_path=args.eval_json,
        rules_path=args.rules_json,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        macro_jsonl=args.macro_jsonl,
    )
    rows = doc.pop("_jsonl_rows", [])
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    jsonl_out = args.output_jsonl if args.output_jsonl.is_absolute() else ROOT / args.output_jsonl
    out.parent.mkdir(parents=True, exist_ok=True)
    jsonl_out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with jsonl_out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    ab = doc.get("scored_forward_ab") or {}
    print(
        f"WROTE: {out} logos_diffs={doc.get('full_month', {}).get('logos_direction_diffs')} "
        f"soft {ab.get('global_logos_soft_hit_rate')}→{ab.get('per_date_logos_macro_gate_soft_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
