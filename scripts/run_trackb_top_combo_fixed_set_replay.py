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
DEFAULT_OUT = ART / "trackb_quaternion_top_combo_fixed_set_replay_latest.json"


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
        "lengths": list(data.get("lengths", [20])),
        "oov_ratios": [float(x) for x in data.get("oov_ratios", [0.1, 0.2])],
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


def _eval(mod: Any, cfg: dict[str, Any]) -> dict[str, Any]:
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
        cfg["lengths"],
        cfg["oov_ratios"],
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
    return {"min_short_bucket_rate": er["min_rate"], "curve": er["curve"]}


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay fixed Track B top combo set on current v6 evaluator.")
    ap.add_argument("--fixed-set", default=str(DEFAULT_FIXED_SET))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    fixed_set_path = Path(args.fixed_set) if Path(args.fixed_set).is_absolute() else (ROOT / args.fixed_set)
    fixed = json.loads(fixed_set_path.read_text(encoding="utf-8"))
    selected = fixed.get("selected") or []
    mod = _load_v6_module()

    rows: list[dict[str, Any]] = []
    for row in selected:
        art_rel = str(row.get("artifact"))
        art_path = Path(art_rel) if Path(art_rel).is_absolute() else (ROOT / art_rel)
        cfg = _cfg_from_artifact(art_path)
        replay = _eval(mod, cfg)
        baseline = float(row.get("score_min_short_bucket_rate", 0.0))
        curr = float(replay["min_short_bucket_rate"])
        rows.append(
            {
                "artifact": str(art_path.relative_to(ROOT)).replace("\\", "/"),
                "baseline_min_short_bucket_rate": baseline,
                "replay_min_short_bucket_rate": curr,
                "delta_replay_minus_baseline": curr - baseline,
                "failure_count_at_selection": int(row.get("failure_count", 0)),
                "config_snapshot": {
                    "weights": row.get("weights"),
                    "stage1_top_k": row.get("stage1_top_k"),
                    "beam_size": row.get("beam_size"),
                    "block_size": row.get("block_size"),
                    "semantic_fallback": row.get("semantic_fallback"),
                },
                "curve": replay.get("curve"),
            }
        )

    rows = sorted(rows, key=lambda r: (-r["replay_min_short_bucket_rate"], r["failure_count_at_selection"], r["artifact"]))
    out = {
        "schema": "trackb_quaternion_top_combo_fixed_set_replay_v1",
        "generated_at_utc": _utc_now(),
        "source_fixed_set": str(fixed_set_path.resolve()).replace("\\", "/"),
        "candidate_count": len(rows),
        "ranking_metric": "replay_min_short_bucket_rate",
        "rows": rows,
        "best_artifact": rows[0]["artifact"] if rows else None,
        "fact_safe_note": "Replay is with current local evaluator; compare deltas before any policy changes.",
        "out_of_scope": "No production promotion, no trading trigger.",
    }
    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
