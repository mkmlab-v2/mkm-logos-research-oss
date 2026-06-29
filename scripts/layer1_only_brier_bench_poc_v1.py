#!/usr/bin/env python3
"""Layer-1-only Brier benchmark PoC — mechanical probabilities, B-track wall only.

Evaluates resolved binary rows in layer1_only_brier_bench_poc_v1 cohort JSON.
Layer 3 narrative must remain pointer-only (layer3_interpretation_ref); never in p fields.

Default: holdout-safe — pending rows are counted but not scored.
Use --allow-simulation only for local [HYPO] validation (never production uplift claims).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_v1_latest.json"
DEFAULT_OUT = ROOT / "reports" / "layer1_only_brier_bench_poc_v1_latest.json"
SCHEMA = "layer1_only_brier_bench_poc_eval_v1"
FORBIDDEN_MODEL_SOURCES = frozenset(
    {
        "logos",
        "myeongri",
        "sasang",
        "layer3",
        "lens_narrative",
        "biblical_narrative",
    }
)

_SIM_OUTCOMES: dict[str, int] = {
    "poc.un_pact_http_2xx_20261231": 1,
    "poc.oecd_foresight_pdf_headings_2027": 0,
    "poc.python314_final_before_20261231": 0,
    "poc.ecb_mro_above_3_5_before_20261231": 1,
    "poc.us_unemployment_below_4pct_2026h2": 1,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def calculate_brier_score(predictions: list[float], outcomes: list[int]) -> float:
    if not predictions or len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must be same non-empty length")
    total = 0.0
    for p, y in zip(predictions, outcomes):
        if not (0.0 <= float(p) <= 1.0):
            raise ValueError(f"probability p={p} must be in [0, 1]")
        if y not in (0, 1):
            raise ValueError(f"outcome y={y} must be 0 or 1")
        total += (float(p) - float(y)) ** 2
    return total / len(predictions)


def calculate_skill_score(bs_model: float, bs_baseline: float) -> float:
    if bs_baseline == 0.0:
        return 0.0 if bs_model == 0.0 else -float("inf")
    return 1.0 - (bs_model / bs_baseline)


def _assert_track_wall(poc_meta: dict[str, Any]) -> None:
    if poc_meta.get("track") != "B":
        raise ValueError("track must be B")
    if poc_meta.get("track_wall") != "B":
        raise ValueError("track_wall must be B")
    if poc_meta.get("auto_bridge_to_a") is not False:
        raise ValueError("auto_bridge_to_a must be false")


def _assert_mechanical_forecast(row: dict[str, Any]) -> None:
    kind = str(row.get("model_source_kind") or "").strip().lower()
    if not kind.startswith("mechanical"):
        raise ValueError(f"{row.get('question_id')}: model_source_kind must be mechanical_*")
    detail = str(row.get("model_source_detail") or "").lower()
    for forbidden in FORBIDDEN_MODEL_SOURCES:
        if forbidden in kind or forbidden in detail:
            raise ValueError(f"{row.get('question_id')}: forbidden Layer-3 source in model fields")


def _outcome_int(row: dict[str, Any]) -> int | None:
    if "outcome" in row and row["outcome"] in (0, 1):
        return int(row["outcome"])
    ob = row.get("outcome_binary")
    if isinstance(ob, bool):
        return 1 if ob else 0
    return None


def _apply_simulation(forecasts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in forecasts:
        qid = str(row.get("question_id") or "")
        if qid not in _SIM_OUTCOMES:
            raise ValueError(f"missing simulation outcome for {qid}")
        cloned = dict(row)
        cloned["status"] = "resolved"
        cloned["outcome"] = _SIM_OUTCOMES[qid]
        cloned["resolution_mode"] = "simulation_hypo_v1"
        out.append(cloned)
    return out


def evaluate_cohort(
    doc: dict[str, Any],
    *,
    allow_simulation: bool = False,
) -> dict[str, Any]:
    if doc.get("schema") != "layer1_only_brier_bench_poc_v1":
        raise ValueError("cohort schema must be layer1_only_brier_bench_poc_v1")

    poc_meta = doc.get("poc_meta") or {}
    _assert_track_wall(poc_meta)

    forecasts = [f for f in (doc.get("forecasts") or []) if isinstance(f, dict)]
    if len(forecasts) != 5:
        raise ValueError("PoC cohort must contain exactly 5 goldilocks forecasts")

    for row in forecasts:
        _assert_mechanical_forecast(row)

    pending = [f for f in forecasts if f.get("status") == "pending"]
    resolved = [f for f in forecasts if f.get("status") == "resolved"]

    eval_mode = "strictly_resolved"
    if not resolved and pending and allow_simulation:
        resolved = _apply_simulation(forecasts)
        eval_mode = "simulation_validated_hypo"
    elif not resolved:
        return {
            "schema": SCHEMA,
            "generated_at_utc": _utc_now(),
            "evaluation_summary": {
                "poc_cohort": poc_meta.get("cohort_id"),
                "track_wall": poc_meta.get("track_wall"),
                "auto_bridge_to_a": poc_meta.get("auto_bridge_to_a"),
                "evaluated_n": 0,
                "pending_n": len(pending),
                "resolved_n": 0,
                "status": "holdout_only",
                "eval_mode": eval_mode,
                "note": "No resolved rows; Brier/BSS withheld until external resolver fires.",
            },
        }

    models_p = [float(f["probability_model_p"]) for f in resolved]
    baselines_p = [float(f["probability_baseline_p"]) for f in resolved]
    baserates_p = [float(f["base_rate_p"]) for f in resolved]
    actual_y = [_outcome_int(f) for f in resolved]
    if any(y is None for y in actual_y):
        raise ValueError("resolved row missing outcome 0/1")

    y_list = [int(y) for y in actual_y if y is not None]
    bs_model = calculate_brier_score(models_p, y_list)
    bs_baseline = calculate_brier_score(baselines_p, y_list)
    bs_baserate = calculate_brier_score(baserates_p, y_list)

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "evaluation_summary": {
            "poc_cohort": poc_meta.get("cohort_id"),
            "track_wall": poc_meta.get("track_wall"),
            "auto_bridge_to_a": poc_meta.get("auto_bridge_to_a"),
            "evaluated_n": len(resolved),
            "pending_n": len([f for f in forecasts if f.get("status") == "pending"]),
            "resolved_n": len(resolved),
            "brier_scores": {
                "model_score": round(bs_model, 6),
                "uniform_baseline_score": round(bs_baseline, 6),
                "baserate_score": round(bs_baserate, 6),
            },
            "skill_scores_uplift": {
                "skill_vs_uniform_0_5": round(calculate_skill_score(bs_model, bs_baseline), 6),
                "skill_vs_historical_baserate": round(calculate_skill_score(bs_model, bs_baserate), 6),
            },
            "status": eval_mode,
            "eval_mode": eval_mode,
            "research_rail": "B",
            "layer3_in_probability_fields": False,
        },
        "rows": [
            {
                "question_id": f.get("question_id"),
                "probability_model_p": f.get("probability_model_p"),
                "probability_baseline_p": f.get("probability_baseline_p"),
                "base_rate_p": f.get("base_rate_p"),
                "outcome": _outcome_int(f),
                "model_source_kind": f.get("model_source_kind"),
            }
            for f in resolved
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--allow-simulation",
        action="store_true",
        help="[HYPO] Resolve all pending rows with fixed stub outcomes for math smoke only.",
    )
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()

    if not ns.cohort.is_file():
        print(f"cohort not found: {ns.cohort}", file=sys.stderr)
        return 2

    try:
        doc = _load(ns.cohort)
        report = evaluate_cohort(doc, allow_simulation=ns.allow_simulation)
    except ValueError as exc:
        print(f"safety/validation error: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    print(payload)
    if not ns.stdout_only:
        ns.output.parent.mkdir(parents=True, exist_ok=True)
        ns.output.write_text(payload + "\n", encoding="utf-8")
        print(f"metrics written to {ns.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
