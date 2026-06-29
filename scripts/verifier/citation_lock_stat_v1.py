#!/usr/bin/env python3
"""CL_stat — Neyman-Pearson bound + self-consistency entropy pre-gate [HYPO].

Extends deterministic citation lock with statistical lower bound (Wilson)
and multi-sample Shannon entropy gate. research_only · send_gate: HOLD.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "docs/final/artifacts/citation_lock_stat_eval_v1_latest.json"

DEFAULT_ALPHA_E = 0.05
DEFAULT_GAMMA = 0.12
DEFAULT_PHI_MIN = 0.88
DEFAULT_MEAN_MIN = 0.85


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def shannon_entropy(outputs: list[str]) -> float:
    if not outputs:
        return 0.0
    counts = Counter(outputs)
    total = len(outputs)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return float(entropy)


def wilson_score_lower(successes: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = p + z2 / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n)
    return max(0.0, (center - margin) / denom)


def compute_cl_stat(
    claims: list[dict[str, Any]],
    sc_outputs: list[str],
    *,
    alpha_e: float = DEFAULT_ALPHA_E,
    gamma: float = DEFAULT_GAMMA,
    phi_min: float = DEFAULT_PHI_MIN,
    mean_min: float = DEFAULT_MEAN_MIN,
) -> dict[str, Any]:
    entropy = shannon_entropy(sc_outputs)
    if entropy > gamma:
        return {
            "schema": "citation_lock_stat_v1",
            "gate_ok": False,
            "reject_reason": "entropy_exceeded",
            "entropy": round(entropy, 6),
            "gamma": gamma,
            "weighted_mean": None,
            "critical_bound": None,
            "wilson_lower_bound": None,
            "claim_count": len(claims),
            "sc_sample_count": len(sc_outputs),
        }

    weighted_scores: list[float] = []
    anchor_passes = 0
    for claim in claims:
        fuzzy_score = float(claim.get("fuzzy_score", 0.0))
        weight = float(claim.get("weight", 1.0))
        phi_score = fuzzy_score if fuzzy_score >= phi_min else 0.0
        weighted_scores.append(phi_score * weight)
        if phi_score > 0.0:
            anchor_passes += 1

    m = len(claims)
    weighted_mean = (sum(weighted_scores) / m) if m else 0.0
    critical_bound = mean_min - (alpha_e * (1.0 / math.sqrt(m))) if m else mean_min
    wilson_lb = wilson_score_lower(anchor_passes, m) if m else 0.0

    mean_ok = weighted_mean >= critical_bound
    pass_rate = (anchor_passes / m) if m else 0.0
    if m >= 10:
        wilson_ok = wilson_lb >= (critical_bound - alpha_e)
    else:
        wilson_ok = pass_rate >= critical_bound
    gate_ok = mean_ok and wilson_ok and m > 0

    return {
        "schema": "citation_lock_stat_v1",
        "gate_ok": gate_ok,
        "reject_reason": None if gate_ok else "stat_threshold_not_met",
        "entropy": round(entropy, 6),
        "gamma": gamma,
        "alpha_e": alpha_e,
        "phi_min": phi_min,
        "weighted_mean": round(weighted_mean, 6),
        "critical_bound": round(critical_bound, 6),
        "wilson_lower_bound": round(wilson_lb, 6),
        "wilson_threshold": round((critical_bound - alpha_e) if m >= 10 else critical_bound, 6),
        "pass_rate": round(pass_rate, 6),
        "anchor_passes": anchor_passes,
        "claim_count": m,
        "sc_sample_count": len(sc_outputs),
        "research_only": True,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claims-json", type=Path, help='JSON list[{"fuzzy_score":0.9,"weight":1.0},...]')
    ap.add_argument("--sc-json", type=Path, help='JSON list of self-consistency output strings')
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--alpha-e", type=float, default=DEFAULT_ALPHA_E)
    ap.add_argument("--gamma", type=float, default=DEFAULT_GAMMA)
    args = ap.parse_args()

    if args.claims_json and args.sc_json:
        claims = json.loads(args.claims_json.read_text(encoding="utf-8"))
        sc_outputs = json.loads(args.sc_json.read_text(encoding="utf-8"))
    else:
        claims = [
            {"fuzzy_score": 0.95, "weight": 1.0},
            {"fuzzy_score": 0.91, "weight": 1.0},
            {"fuzzy_score": 0.90, "weight": 1.0},
            {"fuzzy_score": 0.92, "weight": 1.0},
            {"fuzzy_score": 0.93, "weight": 1.0},
            {"fuzzy_score": 0.94, "weight": 1.0},
        ]
        sc_outputs = ["anchor A verified", "anchor A verified", "anchor A verified"]

    result = compute_cl_stat(
        claims,
        sc_outputs,
        alpha_e=args.alpha_e,
        gamma=args.gamma,
    )
    result["generated_at_utc"] = _utc_now()
    result["reproduce"] = "py scripts/verifier/citation_lock_stat_v1.py"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"gate_ok": result["gate_ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if result["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
