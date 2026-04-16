#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_FIXED_SET = ART / "trackb_quaternion_top_combo_fixed_set_latest.json"
DEFAULT_OUT = ART / "trackb_quaternion_top_combo_stress_grid_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_v6_module():
    path = ROOT / "scripts" / "run_trackb_quaternion_generalization_bench_v6.py"
    spec = importlib.util.spec_from_file_location("trackb_quaternion_generalization_bench_v6", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg_from_artifact(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    best = data.get("best") or {}
    weights = best.get("weights") or {}
    return {
        "weights": (
            float(weights.get("order", 0.3)),
            float(weights.get("set", 0.35)),
            float(weights.get("jaccard", 0.2)),
            float(weights.get("bigram", 0.05)),
        ),
        "seeds": list(data.get("seeds", [])),
        "samples_per_cell": int(data.get("samples_per_cell", 30)),
        "semantic_fallback": bool(data.get("semantic_fallback", False)),
        "fallback_threshold": float(data.get("fallback_threshold", 0.85)),
        "eval_metric": str(data.get("eval_metric", "exact_sequence")),
        "sequence_weight": float(data.get("sequence_weight", 0.45)),
        "include_target_in_candidates": bool(data.get("include_target_in_candidates", False)),
        "two_stage_ranker": bool(data.get("two_stage_ranker", True)),
        "stage1_top_k": int(data.get("stage1_top_k", 32)),
        "blockwise_mode": bool(data.get("blockwise_mode", True)),
        "block_size": int(data.get("block_size", 4)),
        "beam_mode": bool(data.get("beam_mode", True)),
        "beam_size": int(data.get("beam_size", 4)),
        "chunkwise_mode": bool(data.get("chunkwise_mode", False)),
        "chunk_beam_size": int(data.get("chunk_beam_size", 8)),
        "stage2_length_prior": bool(data.get("stage2_length_prior", True)),
        "stage2_swap_guard": bool(data.get("stage2_swap_guard", True)),
        "stage2_swap_injection": bool(data.get("stage2_swap_injection", True)),
        "stage2_order_w_override": float(data.get("stage2_order_w_override", -1.0)),
        "stage2_big_w_override": float(data.get("stage2_big_w_override", -1.0)),
        "stage2_pos_w_override": float(data.get("stage2_pos_w_override", -1.0)),
    }


def _eval_curve(mod: Any, cfg: dict[str, Any], lengths: list[int], oov_ratios: list[float]) -> list[dict[str, Any]]:
    w_order, w_set, w_jac, w_bigram = cfg["weights"]
    er = mod._evaluate_short(
        cfg["seeds"],
        cfg["samples_per_cell"],
        (w_order, w_set, w_jac, w_bigram),
        cfg["semantic_fallback"],
        cfg["fallback_threshold"],
        cfg["eval_metric"],
        cfg["sequence_weight"],
        cfg["include_target_in_candidates"],
        cfg["two_stage_ranker"],
        cfg["stage1_top_k"],
        lengths,
        oov_ratios,
        cfg["blockwise_mode"],
        cfg["block_size"],
        cfg["beam_mode"],
        cfg["beam_size"],
        cfg["chunkwise_mode"],
        cfg["chunk_beam_size"],
        cfg["stage2_length_prior"],
        False,
        0,
        cfg["stage2_swap_guard"],
        cfg["stage2_swap_injection"],
        cfg["stage2_order_w_override"],
        cfg["stage2_big_w_override"],
        cfg["stage2_pos_w_override"],
        0,
        0,
        0,
    )
    return er.get("curve") or []


def _collapse_summary(curve: list[dict[str, Any]], floor: float) -> dict[str, Any]:
    by_len: dict[int, list[dict[str, Any]]] = {}
    for row in curve:
        ln = int(row.get("length", 0))
        by_len.setdefault(ln, []).append(row)
    first_oov_below_floor: dict[str, float | None] = {}
    for ln, rows in by_len.items():
        rows_sorted = sorted(rows, key=lambda r: float(r.get("oov_ratio", 0.0)))
        hit: float | None = None
        for r in rows_sorted:
            rate = float(r.get("exact_sequence_match_rate", 0.0))
            if rate < floor:
                hit = float(r.get("oov_ratio", 0.0))
                break
        first_oov_below_floor[str(ln)] = hit
    min_rate = min((float(r.get("exact_sequence_match_rate", 0.0)) for r in curve), default=0.0)
    return {
        "collapse_floor": floor,
        "first_oov_below_floor_by_length": first_oov_below_floor,
        "min_exact_sequence_match_rate_over_grid": min_rate,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Length/OOV stress grid replay for fixed top combo set.")
    ap.add_argument("--fixed-set", default=str(DEFAULT_FIXED_SET))
    ap.add_argument("--lengths", default="20,24")
    ap.add_argument("--oov-ratios", default="0.1,0.2")
    ap.add_argument("--collapse-floor", type=float, default=0.75)
    ap.add_argument(
        "--samples-per-cell-cap",
        type=int,
        default=0,
        help="Optional upper bound for samples_per_cell used during stress replay (0=disabled).",
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    fixed_path = Path(args.fixed_set) if Path(args.fixed_set).is_absolute() else (ROOT / args.fixed_set)
    fixed = json.loads(fixed_path.read_text(encoding="utf-8"))
    selected = fixed.get("selected") or []
    lengths = [int(x.strip()) for x in args.lengths.split(",") if x.strip()]
    oov_ratios = [float(x.strip()) for x in args.oov_ratios.split(",") if x.strip()]
    mod = _load_v6_module()

    rows: list[dict[str, Any]] = []
    for item in selected:
        art_rel = str(item.get("artifact"))
        art_path = Path(art_rel) if Path(art_rel).is_absolute() else (ROOT / art_rel)
        cfg = _cfg_from_artifact(art_path)
        if args.samples_per_cell_cap > 0:
            cfg["samples_per_cell"] = min(int(cfg.get("samples_per_cell", 0)), args.samples_per_cell_cap)
        curve = _eval_curve(mod, cfg, lengths, oov_ratios)
        summary = _collapse_summary(curve, args.collapse_floor)
        rows.append(
            {
                "artifact": str(art_path.relative_to(ROOT)).replace("\\", "/"),
                "selection_score_min_short_bucket_rate": item.get("score_min_short_bucket_rate"),
                "failure_count_at_selection": item.get("failure_count"),
                "config_snapshot": {
                    "weights": item.get("weights"),
                    "stage1_top_k": item.get("stage1_top_k"),
                    "beam_size": item.get("beam_size"),
                    "block_size": item.get("block_size"),
                    "semantic_fallback": item.get("semantic_fallback"),
                },
                "stress_curve": curve,
                "stress_summary": summary,
            }
        )

    out = {
        "schema": "trackb_quaternion_top_combo_stress_grid_v1",
        "generated_at_utc": _utc_now(),
        "source_fixed_set": str(fixed_path.resolve()).replace("\\", "/"),
        "grid": {"lengths": lengths, "oov_ratios": oov_ratios},
        "samples_per_cell_cap": args.samples_per_cell_cap if args.samples_per_cell_cap > 0 else None,
        "candidate_count": len(rows),
        "rows": rows,
        "fact_safe_note": "Stress grid is research-only and evaluator-specific; do not infer production readiness directly.",
        "out_of_scope": "No production promotion, no trading trigger.",
    }
    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
