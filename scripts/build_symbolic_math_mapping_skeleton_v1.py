#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.91, L:0.86, K:0.71, M:0.46}
# Balance: 90
# Purpose: Build v1 mathematical skeleton for symbolic mapping (Gematria/4D/Quaternion).
# Keywords: gematria, 4d, quaternion, mapping, loss, validation
"""Build symbolic math mapping skeleton v1.

This script produces a deterministic artifact describing:
- 4D vector space contract
- quaternion composition contract
- mapping-loss definition (distance + consistency penalties)
- validation metric set for holdout governance
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quat_mul(a: list[float], b: list[float]) -> list[float]:
    # Hamilton product: (w,x,y,z)
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return [
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    ]


def _l2(vec: list[float]) -> float:
    return sum(v * v for v in vec) ** 0.5


def build_payload(example_weight_distance: float, example_weight_consistency: float) -> dict:
    # Example anchor vectors for deterministic demo calculations.
    anchor_a = [1.0, 0.2, 0.3, 0.4]
    anchor_b = [0.9, 0.1, 0.1, 0.2]
    q_demo = _quat_mul(anchor_a, anchor_b)
    dist_demo = _l2([a - b for a, b in zip(anchor_a, anchor_b)])
    consistency_penalty_demo = abs((sum(anchor_a) / 4.0) - (sum(anchor_b) / 4.0))
    loss_demo = (example_weight_distance * dist_demo) + (
        example_weight_consistency * consistency_penalty_demo
    )

    return {
        "schema": "symbolic_math_mapping_skeleton_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
            "note": "Mathematical skeleton only; no direct live promotion.",
        },
        "space_contract": {
            "vector4d_axes": ["S", "L", "K", "M"],
            "domain_examples": ["anchor", "atom", "symbol", "event", "news_term", "economic_term"],
            "normalization": "per_axis_minmax_or_zscore_before_fusion",
        },
        "quaternion_contract": {
            "format": "wxyz",
            "operation": "hamilton_product",
            "rotation_note": "Use quaternion composition for symbolic transition modeling.",
            "demo": {
                "anchor_a_wxyz": anchor_a,
                "anchor_b_wxyz": anchor_b,
                "hamilton_product_wxyz": [round(x, 6) for x in q_demo],
            },
        },
        "loss_function_contract": {
            "name": "mapping_loss_v1",
            "formula": "L = w_dist * ||v_src - v_tgt||_2 + w_consistency * penalty_consistency",
            "weights": {
                "w_dist": example_weight_distance,
                "w_consistency": example_weight_consistency,
            },
            "demo": {
                "distance_l2": round(dist_demo, 6),
                "consistency_penalty": round(consistency_penalty_demo, 6),
                "mapping_loss": round(loss_demo, 6),
            },
        },
        "validation_metric_contract": {
            "primary": [
                "holdout_accuracy",
                "holdout_permutation_p_value",
                "generalization_gap",
                "mapping_collision_rate",
            ],
            "gate_defaults": {
                "min_holdout_n": 30,
                "min_holdout_accuracy": 0.5,
                "max_generalization_gap": 0.4,
                "max_holdout_p_value": 0.2,
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build symbolic math mapping skeleton v1 artifact.")
    ap.add_argument("--w-dist", type=float, default=0.7)
    ap.add_argument("--w-consistency", type=float, default=0.3)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/symbolic_math_mapping_skeleton_v1_latest.json"),
    )
    ns = ap.parse_args()

    payload = build_payload(ns.w_dist, ns.w_consistency)
    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
