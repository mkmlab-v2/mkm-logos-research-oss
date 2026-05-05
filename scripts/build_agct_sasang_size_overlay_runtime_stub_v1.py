#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.83, K:0.63, M:0.47}
# Balance: 88
# Purpose: Convert AGCT-Sasang overlay candidate into Athena runtime stub (non-gating).
# Keywords: agct, sasang, overlay, runtime, athena, stub
"""Build runtime stub from AGCT-Sasang size overlay candidate.

The output remains research-only and non-gating by default.
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Build AGCT-Sasang runtime size overlay stub.")
    ap.add_argument("--overlay-candidate-json", type=Path, required=True)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_sasang_size_overlay_runtime_stub_v1_latest.json"),
    )
    ap.add_argument("--runtime-enabled", action="store_true", help="Set enabled=true in stub (still non-gating).")
    ns = ap.parse_args()

    src = _load_json(ns.overlay_candidate_json)
    gates = src.get("gates", {})
    candidate_ready = bool(gates.get("candidate_ready_for_human_review"))
    ov = src.get("overlay_candidate", {})

    # Keep runtime disabled by default unless explicitly enabled and candidate is ready.
    enabled = bool(ns.runtime_enabled and candidate_ready)
    status = "READY_FOR_SHADOW" if candidate_ready else "HOLD"
    if not enabled:
        status = f"{status}_DISABLED"

    payload = {
        "schema": "agct_sasang_size_overlay_runtime_stub_v1",
        "generated_at_utc": _utc_now(),
        "source_overlay_candidate_json": str(ns.overlay_candidate_json.resolve()),
        "governance": {
            "track": "B_TRACK",
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
            "auto_live_binding_forbidden": True,
        },
        "runtime_stub": {
            "feature_key": "agct_sasang_size_overlay_v1",
            "enabled": enabled,
            "status": status,
            "mode": "size_multiplier_only",
            "multipliers": {
                "low_risk": float(ov.get("low_risk_multiplier", 1.0)),
                "neutral": float(ov.get("neutral_multiplier", 1.0)),
                "high_risk": float(ov.get("high_risk_multiplier", 1.0)),
            },
            "guards": {
                "require_candidate_ready": candidate_ready,
                "require_human_review_ticket": True,
                "fallback_multiplier": 1.0,
            },
            "evidence": {
                "best_accuracy": src.get("evidence", {}).get("best_accuracy"),
                "best_accuracy_permutation_p_value": src.get("evidence", {}).get("best_accuracy_permutation_p_value"),
                "risk_corr_pearson": src.get("evidence", {}).get("risk_corr_pearson"),
            },
        },
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} enabled={enabled} "
        f"status={status} candidate_ready={candidate_ready}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
