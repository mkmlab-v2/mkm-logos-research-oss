#!/usr/bin/env python3
"""AB: all_v4 vs all_v3 vs hybrid on mixed + swap_typo buckets (research_only)."""

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
OUT_DEFAULT = ART / "l1_inverse_decoder_hybrid_routing_ab_v1_latest.json"
LONGSAMPLE_BASELINE = ART / "l1_inverse_decoder_longsample_gate_harness_baseline_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_seeds(raw: str) -> list[int]:
    vals = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty seeds")
    return vals


def _eval_arm(arm: str, seeds: list[int], forced: str | None, samples: int, beam_size: int, noise_level: float, scoring_mode: str) -> dict[str, Any]:
    prev_disable = os.environ.get("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE")
    prev_hybrid = os.environ.get("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY")
    try:
        if arm == "objective_v4":
            os.environ["L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE"] = "1"
            os.environ.pop("L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY", None)
        elif arm == "mode_router_v3":
            os.environ.pop("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", None)
            os.environ["L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY"] = "0"
        elif arm == "hybrid_swap_typo_v3":
            os.environ.pop("L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE", None)
            os.environ["L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY"] = "1"
        else:
            raise ValueError(arm)

        exact_vals: list[float] = []
        recovery_vals: list[float] = []
        breakdown_acc: dict[str, dict[str, float]] = {}
        hybrid_routes: dict[str, int] | None = None
        for seed in seeds:
            rep, _ = run(
                seed=seed,
                samples=samples,
                beam_size=beam_size,
                noise_level=noise_level,
                scoring_mode=scoring_mode,
                forced_noise_mode=forced,
            )
            exact_vals.append(float(rep["exact_restore_rate"]))
            recovery_vals.append(float(rep["recovery_rate"]))
            if isinstance(rep.get("hybrid_route_counts"), dict):
                hybrid_routes = hybrid_routes or {"v3_swap_typo": 0, "v4_other": 0}
                for k, v in rep["hybrid_route_counts"].items():
                    hybrid_routes[k] = hybrid_routes.get(k, 0) + int(v)
            for mode, row in (rep.get("noise_mode_breakdown") or {}).items():
                acc = breakdown_acc.setdefault(mode, {"n": 0.0, "exact": 0.0, "recover": 0.0})
                n = float(row.get("sample_count") or 0)
                acc["n"] += n
                acc["exact"] += float(row.get("exact_restore_rate") or 0) * n
                acc["recover"] += float(row.get("recovery_rate") or 0) * n
        mode_breakdown = {
            mode: {
                "sample_count": int(acc["n"]),
                "exact_restore_rate": (acc["exact"] / acc["n"]) if acc["n"] else 0.0,
                "recovery_rate": (acc["recover"] / acc["n"]) if acc["n"] else 0.0,
            }
            for mode, acc in breakdown_acc.items()
        }
        return {
            "arm": arm,
            "forced_noise_mode": forced or "mixed",
            "avg_exact_restore_rate": sum(exact_vals) / len(exact_vals),
            "avg_recovery_rate": sum(recovery_vals) / len(recovery_vals),
            "noise_mode_breakdown": mode_breakdown,
            "hybrid_route_counts": hybrid_routes,
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
    ap.add_argument("--seeds", type=str, default="701,809,1009,1103")
    ap.add_argument("--samples", type=int, default=120)
    ap.add_argument("--beam-size", type=int, default=8)
    ap.add_argument("--noise-level", type=float, default=0.1)
    ap.add_argument("--scoring-mode", choices=("legacy", "enhanced", "swap_v2"), default="enhanced")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    seeds = _parse_seeds(args.seeds)
    arms = ("objective_v4", "mode_router_v3", "hybrid_swap_typo_v3")
    scenarios: list[tuple[str, str | None]] = [("mixed", None), ("swap_typo", "swap_typo")]

    scenario_results: dict[str, Any] = {}
    for label, forced in scenarios:
        per_arm = [_eval_arm(a, seeds, forced, args.samples, args.beam_size, args.noise_level, args.scoring_mode) for a in arms]
        v4 = per_arm[0]
        hybrid = per_arm[2]
        v3 = per_arm[1]
        scenario_results[label] = {
            "per_arm": per_arm,
            "delta_hybrid_minus_v4_exact": hybrid["avg_exact_restore_rate"] - v4["avg_exact_restore_rate"],
            "delta_hybrid_minus_v3_exact": hybrid["avg_exact_restore_rate"] - v3["avg_exact_restore_rate"],
            "delta_v3_minus_v4_exact": v3["avg_exact_restore_rate"] - v4["avg_exact_restore_rate"],
        }

    mixed = scenario_results.get("mixed", {})
    hybrid_wins_mixed = mixed.get("delta_hybrid_minus_v3_exact", -1.0) >= -0.0025
    hybrid_beats_v4_mixed = mixed.get("delta_hybrid_minus_v4_exact", -1.0) >= 0.0
    decision = "GO_HYBRID_DEFAULT" if hybrid_wins_mixed and hybrid_beats_v4_mixed else "HOLD_ALL_V3_OR_MANUAL"

    baseline_mixed = None
    if LONGSAMPLE_BASELINE.is_file():
        baseline_mixed = json.loads(LONGSAMPLE_BASELINE.read_text(encoding="utf-8")).get("mixed", {}).get("exact_restore_rate")

    out_doc = {
        "schema": "l1_inverse_decoder_hybrid_routing_ab_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "inputs": {
            "seeds": seeds,
            "samples": args.samples,
            "beam_size": args.beam_size,
            "noise_level": args.noise_level,
            "scoring_mode": args.scoring_mode,
        },
        "scenarios": scenario_results,
        "gate": {
            "mixed_non_regression_floor": -0.005,
            "hybrid_wins_mixed_vs_v3": hybrid_wins_mixed,
            "hybrid_beats_v4_mixed": hybrid_beats_v4_mixed,
            "decision": decision,
            "baseline_mixed_exact_reference": baseline_mixed,
        },
        "default_env": "L1_INVERSE_DECODER_HYBRID_SWAP_TYPO_V3_ONLY=1 (swap_typo→v3, else v4)",
    }

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
