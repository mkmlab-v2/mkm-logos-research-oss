# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Consolidate Week-4 experiments into final policy replay decision.
# Keywords: track_a, week4, policy_replay, decision, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_experiment_pack_v1.json"
E1 = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_domain_phrase_ab_v1.json"
E2 = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_timing_domain_phrase_ab_v1.json"
E3 = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_selective_router_ab_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_policy_replay_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", type=Path, default=PACK)
    ap.add_argument("--e1", type=Path, default=E1)
    ap.add_argument("--e2", type=Path, default=E2)
    ap.add_argument("--e3", type=Path, default=E3)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--policy-floor", type=float, default=0.49)
    args = ap.parse_args()

    pack = _load(args.pack if args.pack.is_absolute() else ROOT / args.pack)
    e1 = _load(args.e1 if args.e1.is_absolute() else ROOT / args.e1)
    e2 = _load(args.e2 if args.e2.is_absolute() else ROOT / args.e2)
    e3 = _load(args.e3 if args.e3.is_absolute() else ROOT / args.e3)

    e1_base = e1.get("baseline") or {}
    e1_treat = (e1.get("treatments") or [{}])[0]
    e2_treat = (e2.get("treatments") or [{}])[0]
    e3_mixed = ((e3.get("metrics") or {}).get("selective_mixed")) or {}

    best_saving = max(
        float(e1_base.get("saving", 0.0)),
        float(e1_treat.get("saving", 0.0)),
        float(e2_treat.get("saving", 0.0)),
        float(e3_mixed.get("global_token_saving_rate", 0.0)),
    )
    best_jaccard = max(
        float(e1_base.get("jaccard", 0.0)),
        float(e1_treat.get("jaccard", 0.0)),
        float(e2_treat.get("jaccard", 0.0)),
        float(e3_mixed.get("avg_reconstruction_fidelity_jaccard", 0.0)),
    )
    best_integrity = max(
        float(e1_base.get("integrity", 0.0)),
        float(e1_treat.get("integrity", 0.0)),
        float(e2_treat.get("integrity", 0.0)),
        float(e3_mixed.get("avg_sensitive_integrity", 0.0)),
    )

    quality_tradeoff_flag = bool((e3.get("gate") or {}).get("jaccard_floor_ok") is False)
    policy_floor_ok = best_saving >= args.policy_floor
    integrity_ok = best_integrity >= 1.0

    decision = (
        "GO_W4_POLICY_REPLAY"
        if policy_floor_ok and integrity_ok and not quality_tradeoff_flag
        else "HOLD_W4_POLICY_REPLAY"
    )

    out_doc = {
        "schema": "track_a_week4_policy_replay_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "pack": str(args.pack),
            "w4_e1": str(args.e1),
            "w4_e2": str(args.e2),
            "w4_e3": str(args.e3),
        },
        "week4_summary": {
            "entry_replay_decision": (pack.get("entry_condition") or {}).get("replay_decision"),
            "e1_decision": e1.get("decision"),
            "e2_decision": e2.get("decision"),
            "e3_decision": e3.get("decision"),
            "e1_viable_count": int(e1.get("viable_count", 0)),
            "e2_viable_count": int(e2.get("viable_count", 0)),
            "e3_gate": e3.get("gate"),
        },
        "replay_checks": {
            "policy_floor": args.policy_floor,
            "best_saving_seen": best_saving,
            "best_jaccard_seen": best_jaccard,
            "best_integrity_seen": best_integrity,
            "policy_floor_ok": policy_floor_ok,
            "integrity_ok": integrity_ok,
            "quality_tradeoff_flag": quality_tradeoff_flag,
        },
        "decision": decision,
        "next_action": (
            "Start Week-5 engine-level routing rule redesign under fixed 0.49 floor."
            if decision == "HOLD_W4_POLICY_REPLAY"
            else "Prepare commercialization replay promotion package under unchanged floor."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
