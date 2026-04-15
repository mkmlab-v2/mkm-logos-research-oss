# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Generate Week-3 D4 policy-floor replay decision artifact.
# Keywords: track_a, policy_floor, replay, decision, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ROUTING = ROOT / "docs" / "final" / "artifacts" / "track_a_routing_condition_ab_v1.json"
CAP = ROOT / "docs" / "final" / "artifacts" / "track_a_cap_decouple_sweep_v1.json"
PHRASE = ROOT / "docs" / "final" / "artifacts" / "track_a_phrase_profile_ab_v1.json"
POLICY = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_decision_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_policy_floor_replay_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--routing", type=Path, default=ROUTING)
    ap.add_argument("--cap", type=Path, default=CAP)
    ap.add_argument("--phrase", type=Path, default=PHRASE)
    ap.add_argument("--policy", type=Path, default=POLICY)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--policy-floor", type=float, default=0.49)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    routing = _load(args.routing if args.routing.is_absolute() else ROOT / args.routing)
    cap = _load(args.cap if args.cap.is_absolute() else ROOT / args.cap)
    phrase = _load(args.phrase if args.phrase.is_absolute() else ROOT / args.phrase)
    policy = _load(args.policy if args.policy.is_absolute() else ROOT / args.policy)

    router_on = (routing.get("arms") or {}).get("arm_a_router_on") or {}
    router_off = (routing.get("arms") or {}).get("arm_b_router_off") or {}
    phrase_baseline = phrase.get("baseline_router_on") or {}

    best_saving_seen = max(
        float(router_on.get("saving", 0.0)),
        float(router_off.get("saving", 0.0)),
        float((cap.get("best_jaccard_observed") or {}).get("saving", 0.0)),
        float(phrase_baseline.get("saving", 0.0)),
    )
    best_jaccard_seen = max(
        float(router_on.get("jaccard", 0.0)),
        float(router_off.get("jaccard", 0.0)),
        float((cap.get("best_jaccard_observed") or {}).get("jaccard", 0.0)),
        float(phrase_baseline.get("jaccard", 0.0)),
    )
    best_integrity_seen = max(
        float(router_on.get("integrity", 0.0)),
        float(router_off.get("integrity", 0.0)),
        float((cap.get("best_jaccard_observed") or {}).get("integrity", 0.0)),
        float(phrase_baseline.get("integrity", 0.0)),
    )

    policy_floor_ok = best_saving_seen >= args.policy_floor
    integrity_ok = best_integrity_seen >= args.integrity_floor
    quality_tradeoff_flag = float(router_off.get("jaccard", 0.0)) < float(router_on.get("jaccard", 0.0)) - 0.2

    decision = (
        "GO_POLICY_FLOOR_REPLAY"
        if policy_floor_ok and integrity_ok and not quality_tradeoff_flag
        else "HOLD_POLICY_FLOOR_REPLAY"
    )

    out_doc = {
        "schema": "track_a_policy_floor_replay_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "routing_ab": str(args.routing),
            "cap_decouple": str(args.cap),
            "phrase_profile": str(args.phrase),
            "policy_decision": str(args.policy),
        },
        "policy_context": {
            "policy_floor": args.policy_floor,
            "policy_decision": policy.get("decision"),
            "policy_rationale": policy.get("rationale"),
        },
        "week3_summary": {
            "d1_decision": routing.get("decision"),
            "d2_decision": cap.get("decision"),
            "d3_decision": phrase.get("decision"),
            "d2_viable_count": int(cap.get("viable_count", 0)),
            "d3_viable_count": int(phrase.get("viable_count", 0)),
        },
        "replay_checks": {
            "best_saving_seen": best_saving_seen,
            "best_jaccard_seen": best_jaccard_seen,
            "best_integrity_seen": best_integrity_seen,
            "policy_floor_ok": policy_floor_ok,
            "integrity_ok": integrity_ok,
            "quality_tradeoff_flag": quality_tradeoff_flag,
        },
        "decision": decision,
        "next_action": (
            "Register Week-4 experiment pack (domain-specific phrase policies and selective router constraints)."
            if decision == "HOLD_POLICY_FLOOR_REPLAY"
            else "Prepare commercialization replay promotion package with unchanged policy floor."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
