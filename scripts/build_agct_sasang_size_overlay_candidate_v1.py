#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.85, K:0.64, M:0.44}
# Balance: 89
# Purpose: Build research-only size overlay candidate from DNA readiness + AGCT sweep evidence.
# Keywords: bio, dna, sasang, overlay, size_multiplier, governance
"""Build AGCT-Sasang size overlay candidate (B-track, non-gating).

This script reads:
- bio_dna_promotion_readiness_v1
- agct_sasang_hypothesis_sweep_v1

And emits a conservative overlay candidate that can be reviewed by humans before
any runtime wiring.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build AGCT-Sasang size overlay candidate.")
    ap.add_argument("--readiness-json", type=Path, required=True)
    ap.add_argument("--sweep-json", type=Path, required=True)
    ap.add_argument("--min-best-accuracy", type=float, default=0.45)
    ap.add_argument("--max-permutation-pvalue", type=float, default=0.10)
    ap.add_argument("--max-abs-corr", type=float, default=0.50)
    ap.add_argument("--base-size-multiplier", type=float, default=1.0)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_sasang_size_overlay_candidate_v1_latest.json"),
    )
    ns = ap.parse_args()

    readiness = _load_json(ns.readiness_json)
    sweep = _load_json(ns.sweep_json)

    ready = bool(readiness.get("summary", {}).get("promotion_candidate_ready"))
    best_acc = float(sweep.get("summary", {}).get("best_accuracy") or 0.0)
    p_value = sweep.get("summary", {}).get("best_accuracy_permutation_p_value")
    p_value_f = float(p_value) if p_value is not None else 1.0
    top = sweep.get("top_hypotheses") or []
    top_row = top[0] if top else {}
    corr = top_row.get("risk_overlay", {}).get("pearson_corr")
    corr_f = float(corr) if corr is not None else 0.0

    checks = {
        "readiness_gate": ready,
        "best_accuracy_gate": best_acc >= float(ns.min_best_accuracy),
        "permutation_significance_gate": p_value_f <= float(ns.max_permutation_pvalue),
    }
    candidate_ready = all(checks.values())

    corr_norm = _clamp(abs(corr_f) / max(float(ns.max_abs_corr), 1e-6), 0.0, 1.0)
    # Conservative profile: reduce size more aggressively on negative signal.
    low_risk_multiplier = _clamp(float(ns.base_size_multiplier) * (1.0 - 0.10 * corr_norm), 0.80, 1.05)
    neutral_multiplier = _clamp(float(ns.base_size_multiplier) * (1.0 - 0.20 * corr_norm), 0.70, 1.00)
    high_risk_multiplier = _clamp(float(ns.base_size_multiplier) * (1.0 - 0.35 * corr_norm), 0.55, 0.95)

    payload = {
        "schema": "agct_sasang_size_overlay_candidate_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
            "auto_live_binding_forbidden": True,
        },
        "inputs": {
            "readiness_json": str(ns.readiness_json.resolve()),
            "sweep_json": str(ns.sweep_json.resolve()),
        },
        "gates": {
            "thresholds": {
                "min_best_accuracy": float(ns.min_best_accuracy),
                "max_permutation_pvalue": float(ns.max_permutation_pvalue),
            },
            "checks": checks,
            "candidate_ready_for_human_review": candidate_ready,
        },
        "evidence": {
            "best_accuracy": best_acc,
            "best_accuracy_permutation_p_value": p_value_f,
            "top_hypothesis_mapping": top_row.get("mapping"),
            "risk_corr_pearson": corr_f,
        },
        "overlay_candidate": {
            "mode": "size_multiplier_only",
            "base_size_multiplier": float(ns.base_size_multiplier),
            "low_risk_multiplier": round(low_risk_multiplier, 4),
            "neutral_multiplier": round(neutral_multiplier, 4),
            "high_risk_multiplier": round(high_risk_multiplier, 4),
            "note": "Multiplier profile is advisory; runtime wiring requires separate human approval.",
        },
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} candidate_ready={candidate_ready} "
        f"acc={best_acc:.4f} p={p_value_f:.4f} corr={corr_f:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
