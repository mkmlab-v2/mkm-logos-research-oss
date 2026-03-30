#!/usr/bin/env python3
"""Run ultra compression benchmark rounds and emit decision artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report


INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
OUT_ROUND1 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ROUND1_V1.json"
OUT_ROUND2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ROUND2_V1.json"
OUT_DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
OUT_BASELINE_LOCK = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_BASELINE_LOCK_V1.json"

SASANG_TERMS = {
    "사상의학",
    "체질",
    "sasang",
    "태양인",
    "태음인",
    "소양인",
    "소음인",
    "myeongri",
    "bible",
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run 15-day ultra compression benchmark workflow.")
    p.add_argument("--input", default=str(INPUT_V2), help="Input eval spec")
    p.add_argument("--baseline", default=str(BASELINE_V2), help="Baseline report")
    p.add_argument("--jaccard-drop-threshold-pp", type=float, default=1.5, help="Allowed drop")
    return p


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _score(row: dict[str, Any]) -> tuple[float, float]:
    # Prefer high saving, then low jaccard drop.
    return (float(row["global_token_saving_rate"]), -float(row["jaccard_drop_pp"]))


def _pareto_top_two(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=_score, reverse=True)
    return ranked[:2]


def _top_per_hangul_flag(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for flag in (False, True):
        subset = [r for r in rows if bool(r.get("use_hangul_principle", False)) == flag]
        if not subset:
            continue
        selected.append(sorted(subset, key=_score, reverse=True)[0])
    return selected


def _cap_grid() -> list[tuple[float, float, float]]:
    # Include near-target caps so token-level rounding can still hit >=50%.
    general_caps = (0.54, 0.53, 0.52, 0.50, 0.48, 0.46, 0.44)
    sensitive_caps = (0.50, 0.49, 0.47, 0.46, 0.44, 0.42, 0.40)
    hangul_caps = (0.48, 0.46, 0.44, 0.42, 0.40, 0.38)
    grid: list[tuple[float, float, float]] = []
    for gc in general_caps:
        for sc in sensitive_caps:
            for hc in hangul_caps:
                if sc <= gc and hc <= sc:
                    grid.append((gc, sc, hc))
    return grid


def main() -> int:
    args = _parser().parse_args()
    input_path = Path(args.input).resolve()
    baseline_path = Path(args.baseline).resolve()
    src_doc = _load_json(input_path)
    baseline = _load_json(baseline_path)
    baseline_avg_jaccard = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    baseline_saving = float(baseline.get("compression_metrics", {}).get("global_token_saving_rate", 0.0))

    baseline_lock = {
        "schema": "multilens_ultra_compression_baseline_lock_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_input": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        "baseline_report": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json",
        "baseline_global_token_saving_rate": baseline_saving,
        "baseline_avg_reconstruction_fidelity_jaccard": baseline_avg_jaccard,
        "targets": {
            "saving_target": 0.50,
            "jaccard_drop_threshold_pp": args.jaccard_drop_threshold_pp,
        },
    }
    OUT_BASELINE_LOCK.write_text(json.dumps(baseline_lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    strategies = ("A", "B", "C")
    intensities = ("high", "ultra", "extreme")
    round1_rows: list[dict[str, Any]] = []
    for strategy in strategies:
        for intensity in intensities:
            for use_hangul_principle in (False, True):
                rep = evaluate_report(
                    src_doc,
                    source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
                    mode="experimental",
                    strategy=strategy,
                    intensity=intensity,
                    must_keep=set(),
                    jaccard_drop_threshold_pp=args.jaccard_drop_threshold_pp,
                    baseline_avg_jaccard=baseline_avg_jaccard,
                    use_hangul_principle=use_hangul_principle,
                    use_domain_router=True,
                )
                q = rep["quality_gate"]
                c = rep["compression_metrics"]
                round1_rows.append(
                    {
                        "strategy": strategy,
                        "intensity": intensity,
                        "use_hangul_principle": use_hangul_principle,
                        "global_token_saving_rate": c["global_token_saving_rate"],
                        "avg_reconstruction_fidelity_jaccard": c["avg_reconstruction_fidelity_jaccard"],
                        "jaccard_drop_pp": q["jaccard_drop_pp"],
                        "ultra_saving_50_ok": q["ultra_saving_50_ok"],
                        "jaccard_guardrail_ok": q["jaccard_guardrail_ok"],
                        "sensitive_integrity_ok": q["sensitive_integrity_ok"],
                    }
                )
    pareto = _pareto_top_two(round1_rows)
    seed_map: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in pareto + _top_per_hangul_flag(round1_rows):
        key = (row["strategy"], row["intensity"], bool(row.get("use_hangul_principle", False)))
        seed_map[key] = row
    round2_seeds = list(seed_map.values())
    round1 = {
        "schema": "multilens_ultra_compression_round1_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(round1_rows),
        "candidates": round1_rows,
        "pareto_top2": pareto,
        "round2_seed_candidates": round2_seeds,
    }
    OUT_ROUND1.write_text(json.dumps(round1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    round2_rows: list[dict[str, Any]] = []
    for top in round2_seeds:
        strategy = str(top["strategy"])
        intensity = str(top["intensity"])
        use_hangul_principle = bool(top.get("use_hangul_principle", False))
        for general_cap, sensitive_cap, hangul_cap in _cap_grid():
            rep = evaluate_report(
                src_doc,
                source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
                mode="experimental",
                strategy=strategy,
                intensity=intensity,
                must_keep=SASANG_TERMS,
                jaccard_drop_threshold_pp=args.jaccard_drop_threshold_pp,
                baseline_avg_jaccard=baseline_avg_jaccard,
                general_max_saving_rate=general_cap,
                sensitive_max_saving_rate=sensitive_cap,
                hangul_max_saving_rate=hangul_cap,
                use_hangul_principle=use_hangul_principle,
                use_domain_router=True,
            )
            q = rep["quality_gate"]
            c = rep["compression_metrics"]
            # Canary proxy: all three gates pass.
            canary_ok = bool(q["ultra_saving_50_ok"] and q["jaccard_guardrail_ok"] and q["sensitive_integrity_ok"])
            round2_rows.append(
                {
                    "strategy": strategy,
                    "intensity": intensity,
                    "use_hangul_principle": use_hangul_principle,
                    "general_max_saving_rate": general_cap,
                    "sensitive_max_saving_rate": sensitive_cap,
                    "hangul_max_saving_rate": hangul_cap,
                    "global_token_saving_rate": c["global_token_saving_rate"],
                    "avg_reconstruction_fidelity_jaccard": c["avg_reconstruction_fidelity_jaccard"],
                    "avg_sensitive_integrity": c["avg_sensitive_integrity"],
                    "jaccard_drop_pp": q["jaccard_drop_pp"],
                    "canary_gate_ok": canary_ok,
                }
            )
    passing_rows = [r for r in round2_rows if r["canary_gate_ok"]]
    best_round2 = sorted(passing_rows or round2_rows, key=_score, reverse=True)[0] if round2_rows else None
    round2 = {
        "schema": "multilens_ultra_compression_round2_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "guardrail_terms": sorted(SASANG_TERMS),
        "candidates": round2_rows,
        "selected_candidate": best_round2,
    }
    OUT_ROUND2.write_text(json.dumps(round2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    go = bool(best_round2 and best_round2["canary_gate_ok"])
    canary_policy = {
        "traffic_percent": 10,
        "monitoring_metrics": [
            "global_token_saving_rate",
            "jaccard_drop_pp",
            "avg_sensitive_integrity",
            "failure_rate_delta_pp",
            "p95_latency_delta_pct",
        ],
        "thresholds": {
            "saving_rate_min": 0.50,
            "jaccard_drop_pp_max": args.jaccard_drop_threshold_pp,
            "sensitive_integrity_min": 0.999,
            "failure_rate_delta_pp_max": 0.3,
            "p95_latency_delta_pct_max": 15.0,
        },
        "auto_rollback_when_any": [
            "global_token_saving_rate < saving_rate_min",
            "jaccard_drop_pp > jaccard_drop_pp_max",
            "avg_sensitive_integrity < sensitive_integrity_min",
            "failure_rate_delta_pp > failure_rate_delta_pp_max",
            "p95_latency_delta_pct > p95_latency_delta_pct_max",
        ],
    }
    decision = {
        "schema": "multilens_ultra_compression_decision_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "target": {"saving_rate": 0.50, "jaccard_drop_threshold_pp": args.jaccard_drop_threshold_pp},
        "baseline": {
            "global_token_saving_rate": baseline_saving,
            "avg_reconstruction_fidelity_jaccard": baseline_avg_jaccard,
        },
        "selected_candidate": best_round2,
        "go_no_go": "GO" if go else "NO_GO",
        "rollout_policy": "global_default" if go else "domain_variable_cap",
        "canary_policy": canary_policy,
        "notes": "If NO_GO, keep baseline and apply domain-variable compression caps.",
    }
    OUT_DECISION.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_BASELINE_LOCK}")
    print(f"WROTE: {OUT_ROUND1}")
    print(f"WROTE: {OUT_ROUND2}")
    print(f"WROTE: {OUT_DECISION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
