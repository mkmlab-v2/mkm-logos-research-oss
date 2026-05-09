#!/usr/bin/env python3
"""Run GPU->Edge optimization sweep (simulation-first, research_only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "gpu_sim_to_edge_sweep_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _score_candidate(
    *,
    method: str,
    precision: str,
    distill_mode: str,
    model_size_m: int,
    batch_size: int,
    target_p99_ms: float,
) -> dict[str, Any]:
    # Deterministic simulation proxy (not real hardware measurement).
    precision_penalty = {"fp32": 1.0, "fp16": 0.86, "fp8": 0.74, "int8": 0.66, "int4": 0.58}[precision]
    quant_risk = {"none": 0.00, "ptq": 0.03, "awq": 0.04, "qat": 0.02}[method]
    distill_bonus = {"none": 0.00, "teacher_small": 0.01, "teacher_large": 0.02, "teacher_ensemble": 0.03}[
        distill_mode
    ]
    distill_latency_factor = {"none": 1.00, "teacher_small": 0.96, "teacher_large": 0.93, "teacher_ensemble": 0.90}[
        distill_mode
    ]
    size_factor = max(0.55, min(1.35, model_size_m / 80.0))
    batch_factor = max(0.8, min(1.2, batch_size / 8.0))

    # Latency proxy (lower is better)
    p99_ms = round(18.0 * precision_penalty * size_factor * distill_latency_factor / batch_factor, 3)
    p95_ms = round(p99_ms * 0.82, 3)
    p50_ms = round(p99_ms * 0.34, 3)

    # Quality proxy (higher is better)
    base_quality = 0.93 - (0.08 if precision in {"int4"} else 0.03 if precision in {"int8"} else 0.0)
    quality = max(0.0, min(1.0, base_quality - quant_risk + distill_bonus + (0.01 if method == "qat" else 0.0)))

    # Safety proxy (higher is better)
    safety = max(0.0, min(1.0, quality - (0.02 if precision in {"int4"} else 0.0)))

    # Objective: favor meeting target p99 while preserving quality/safety.
    latency_score = max(0.0, min(1.0, target_p99_ms / max(target_p99_ms, p99_ms)))
    overall = round(0.45 * latency_score + 0.35 * quality + 0.20 * safety, 6)

    compression_ratio_est = round(max(0.0, 1.0 - (model_size_m / 120.0)), 6)
    return {
        "method": method,
        "precision": precision,
        "distill_mode": distill_mode,
        "model_size_m": model_size_m,
        "batch_size": batch_size,
        "metrics": {
            "p50_ms": p50_ms,
            "p95_ms": p95_ms,
            "p99_ms": p99_ms,
            "quality_score_0_1": round(quality, 6),
            "safety_score_0_1": round(safety, 6),
            "compression_ratio_est_0_1": compression_ratio_est,
            "target_p99_met": p99_ms <= target_p99_ms,
        },
        "objective_score_0_1": overall,
        "notes": "simulation proxy only; final decision requires target-board measurement",
    }


def _generate_grid(model_sizes: list[int], batch_sizes: list[int]) -> list[dict[str, Any]]:
    methods = ["none", "ptq", "awq", "qat"]
    precisions = ["fp32", "fp16", "fp8", "int8", "int4"]
    distill_modes = ["none", "teacher_small", "teacher_large", "teacher_ensemble"]
    grid = []
    for m in methods:
        for p in precisions:
            for d in distill_modes:
                for ms in model_sizes:
                    for bs in batch_sizes:
                        grid.append(
                            {
                                "method": m,
                                "precision": p,
                                "distill_mode": d,
                                "model_size_m": ms,
                                "batch_size": bs,
                            }
                        )
    return grid


def _parse_csv_ints(raw: str) -> list[int]:
    values = []
    for chunk in raw.split(","):
        c = chunk.strip()
        if not c:
            continue
        values.append(int(c))
    if not values:
        raise ValueError("At least one integer value is required.")
    return values


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-p99-ms", type=float, default=40.0)
    ap.add_argument("--model-sizes-m", default="40,60,80,100")
    ap.add_argument("--batch-sizes", default="4,8,12")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    model_sizes = _parse_csv_ints(args.model_sizes_m)
    batch_sizes = _parse_csv_ints(args.batch_sizes)
    candidates = _generate_grid(model_sizes, batch_sizes)

    scored = [
        _score_candidate(
            method=c["method"],
            precision=c["precision"],
            distill_mode=c["distill_mode"],
            model_size_m=c["model_size_m"],
            batch_size=c["batch_size"],
            target_p99_ms=float(args.target_p99_ms),
        )
        for c in candidates
    ]
    scored.sort(key=lambda x: x["objective_score_0_1"], reverse=True)
    top_k = max(1, int(args.top_k))
    selected = scored[:top_k]

    output = {
        "schema": "gpu_sim_to_edge_sweep_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {
            "target_p99_ms": float(args.target_p99_ms),
            "model_sizes_m": model_sizes,
            "batch_sizes": batch_sizes,
            "top_k": top_k,
        },
        "summary": {
            "candidate_count": len(scored),
            "selected_count": len(selected),
            "best_objective_score_0_1": selected[0]["objective_score_0_1"],
            "best_target_p99_met": selected[0]["metrics"]["target_p99_met"],
        },
        "selected_candidates": selected,
        "all_candidates": scored,
        "constraints": {
            "simulation_not_target_board_measurement": True,
            "final_promotion_requires_target_board_measurement": True,
            "no_auto_live_binding": True,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "best_score": output["summary"]["best_objective_score_0_1"],
                "selected_count": len(selected),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
