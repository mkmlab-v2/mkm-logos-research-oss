# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Summarize Week-22 rebaseline options from latest spike evidence.
# Keywords: track_a, week22, rebaseline, policy_floor, options
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPIKE = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e2_candidate_pool_spike_greedy_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_rebaseline_options_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spike", type=Path, default=SPIKE)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--policy-floor", type=float, default=0.49)
    ap.add_argument("--jaccard-floor", type=float, default=0.85)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    spike = _load(args.spike if args.spike.is_absolute() else ROOT / args.spike)
    m = spike.get("metrics") or {}
    saving = float(m.get("global_token_saving_rate", 0.0))
    jaccard = float(m.get("avg_reconstruction_fidelity_jaccard", 0.0))
    integrity = float(m.get("avg_sensitive_integrity", 0.0))

    hard_gap = max(0.0, float(args.policy_floor) - saving)
    aligned_floor = round(saving, 6)
    quality_ok = jaccard >= float(args.jaccard_floor)
    integrity_ok = integrity >= float(args.integrity_floor)

    out_doc: dict[str, Any] = {
        "schema": "track_a_week22_rebaseline_options_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "spike": str(args.spike),
            "policy_floor": float(args.policy_floor),
            "jaccard_floor": float(args.jaccard_floor),
            "integrity_floor": float(args.integrity_floor),
        },
        "current_best_observed": {
            "saving": saving,
            "jaccard": jaccard,
            "integrity": integrity,
            "quality_ok": quality_ok,
            "integrity_ok": integrity_ok,
        },
        "options": [
            {
                "id": "A_KEEP_FLOOR_049",
                "description": "Keep current policy floor 0.49 and continue generator-level R&D only.",
                "effective_floor": float(args.policy_floor),
                "saving_gap": hard_gap,
                "decision_if_applied_now": "HOLD",
            },
            {
                "id": "B_TEMP_ALIGN_FLOOR_TO_OBSERVED",
                "description": "Temporarily align floor to current observed saving band for controlled rollout.",
                "effective_floor": aligned_floor,
                "saving_gap": 0.0,
                "decision_if_applied_now": (
                    "GO_CONDITIONAL"
                    if quality_ok and integrity_ok
                    else "HOLD"
                ),
            },
        ],
        "recommended": "A_KEEP_FLOOR_049",
        "recommendation_reason": (
            "Quality/integrity are healthy but saving is below commercialization floor; "
            "temporary floor alignment changes policy semantics and should require explicit product decision."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "recommended": out_doc["recommended"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
