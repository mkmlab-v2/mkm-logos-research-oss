#!/usr/bin/env python3
"""Compare v4 vs v3 vs hybrid on typo / oov / swap_typo forced buckets (research_only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.l1_inverse_decoder_decode_router_v1 import run

ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "l1_inverse_decoder_typo_oov_bucket_eval_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty seeds")
    return vals


def _avg_metric(seeds: list[int], samples: int, beam_size: int, noise_level: float, scoring_mode: str, forced: str | None, arm: str) -> dict[str, Any]:
    prev_disable = os.environ.get("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE")
    prev_hybrid = os.environ.get("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY")
    try:
        if arm == "objective_v4":
            os.environ["L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE"] = "1"
            os.environ.pop("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", None)
            runner = run
        elif arm == "mode_router_v3":
            os.environ.pop("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", None)
            os.environ["L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY"] = "0"
            runner = run
        elif arm == "hybrid_swap_typo_v3":
            os.environ.pop("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", None)
            os.environ["L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY"] = "1"
            runner = run
        else:
            raise ValueError(f"unknown arm: {arm}")

        exact_vals: list[float] = []
        recovery_vals: list[float] = []
        decoder_paths: list[str] = []
        for seed in seeds:
            rep, _ = runner(
                seed=seed,
                samples=samples,
                beam_size=beam_size,
                noise_level=noise_level,
                scoring_mode=scoring_mode,
                forced_noise_mode=forced,
            )
            exact_vals.append(float(rep["exact_restore_rate"]))
            recovery_vals.append(float(rep["recovery_rate"]))
            decoder_paths.append(str(rep.get("decoder_path", "")))
        return {
            "arm": arm,
            "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
            "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
            "decoder_path_sample": decoder_paths[0] if decoder_paths else None,
        }
    finally:
        if prev_disable is None:
            os.environ.pop("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", None)
        else:
            os.environ["L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE"] = prev_disable
        if prev_hybrid is None:
            os.environ.pop("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", None)
        else:
            os.environ["L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY"] = prev_hybrid


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=str, default="701,809,907")
    ap.add_argument("--samples", type=int, default=120)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)
    arms = ("objective_v4", "mode_router_v3", "hybrid_swap_typo_v3")
    buckets = ("typo", "oov", "swap_typo")
    results: dict[str, Any] = {}
    for bucket in buckets:
        bucket_rows = []
        for arm in arms:
            bucket_rows.append(
                _avg_metric(
                    seeds,
                    args.samples,
                    args.beam_size,
                    args.noise_level,
                    args.scoring_mode,
                    bucket,
                    arm,
                )
            )
        v4_exact = bucket_rows[0]["avg_exact_restore_rate"]
        best_arm = max(bucket_rows, key=lambda r: r["avg_exact_restore_rate"])
        results[bucket] = {
            "per_arm": bucket_rows,
            "delta_best_minus_v4_exact": best_arm["avg_exact_restore_rate"] - v4_exact,
            "recommended_arm": best_arm["arm"],
        }

    out_doc = {
        "schema": "l1_inverse_decoder_typo_oov_bucket_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
            "arms": list(arms),
            "buckets": list(buckets),
        },
        "results": results,
        "interpretation": {
            "typo_oov_focus": "hybrid routes typo/oov to v4 by design; v3 all-arm is diagnostic only.",
            "track_a_merge": False,
        },
    }

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "swap_typo_best": results["swap_typo"]["recommended_arm"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
