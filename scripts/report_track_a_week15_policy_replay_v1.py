# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Consolidate Week-15 experiments into final policy replay decision.
# Keywords: track_a, week15, policy_replay, decision, commercialization
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week15_hypothesis_pack_v1.json"
E1 = ROOT / "docs" / "final" / "artifacts" / "track_a_week15_selective_floor_unlock_sweep_v1.json"
E2 = ROOT / "docs" / "final" / "artifacts" / "track_a_week15_confidence_replay_crossover_sweep_v1.json"
E3 = ROOT / "docs" / "final" / "artifacts" / "track_a_week15_adaptive_throttle_veto_sweep_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week15_policy_replay_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _best_run(doc: dict[str, Any]) -> dict[str, Any]:
    runs = doc.get("runs") or []
    if not runs:
        return {}
    return sorted(
        runs,
        key=lambda r: (
            float((r.get("metrics") or {}).get("avg_reconstruction_fidelity_jaccard", 0.0)),
            float((r.get("metrics") or {}).get("global_token_saving_rate", 0.0)),
        ),
        reverse=True,
    )[0]


def _read_e4_config(pack: dict[str, Any]) -> tuple[float, bool]:
    exps = ((pack.get("pack") or {}).get("experiments") or [])
    e4 = next((x for x in exps if str(x.get("id")) == "W15-E4"), {})
    cfg = e4.get("config") or {}
    policy_floor = float(cfg.get("policy_floor", 0.49))
    require_quality_tradeoff_flag = bool(cfg.get("require_quality_tradeoff_flag", False))
    return policy_floor, require_quality_tradeoff_flag


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", type=Path, default=PACK)
    ap.add_argument("--e1", type=Path, default=E1)
    ap.add_argument("--e2", type=Path, default=E2)
    ap.add_argument("--e3", type=Path, default=E3)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    pack = _load(args.pack if args.pack.is_absolute() else ROOT / args.pack)
    e1 = _load(args.e1 if args.e1.is_absolute() else ROOT / args.e1)
    e2 = _load(args.e2 if args.e2.is_absolute() else ROOT / args.e2)
    e3 = _load(args.e3 if args.e3.is_absolute() else ROOT / args.e3)
    policy_floor, require_quality_tradeoff_flag = _read_e4_config(pack)

    baseline = e1.get("baseline_router_on") or {}
    best_e1 = _best_run(e1)
    best_e2 = _best_run(e2)
    best_e3 = _best_run(e3)

    saving_candidates = [
        float(baseline.get("global_token_saving_rate", 0.0)),
        float((best_e1.get("metrics") or {}).get("global_token_saving_rate", 0.0)),
        float((best_e2.get("metrics") or {}).get("global_token_saving_rate", 0.0)),
        float((best_e3.get("metrics") or {}).get("global_token_saving_rate", 0.0)),
    ]
    jaccard_candidates = [
        float(baseline.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        float((best_e1.get("metrics") or {}).get("avg_reconstruction_fidelity_jaccard", 0.0)),
        float((best_e2.get("metrics") or {}).get("avg_reconstruction_fidelity_jaccard", 0.0)),
        float((best_e3.get("metrics") or {}).get("avg_reconstruction_fidelity_jaccard", 0.0)),
    ]
    integrity_candidates = [
        float(baseline.get("avg_sensitive_integrity", 0.0)),
        float((best_e1.get("metrics") or {}).get("avg_sensitive_integrity", 0.0)),
        float((best_e2.get("metrics") or {}).get("avg_sensitive_integrity", 0.0)),
        float((best_e3.get("metrics") or {}).get("avg_sensitive_integrity", 0.0)),
    ]

    best_saving = max(saving_candidates)
    best_jaccard = max(jaccard_candidates)
    best_integrity = max(integrity_candidates)

    policy_floor_ok = best_saving >= policy_floor
    integrity_ok = best_integrity >= 1.0
    quality_tradeoff_flag = not any(int(doc.get("viable_count", 0)) > 0 for doc in (e1, e2, e3))
    quality_tradeoff_ok = quality_tradeoff_flag == require_quality_tradeoff_flag

    decision = (
        "GO_W15_POLICY_REPLAY"
        if policy_floor_ok and integrity_ok and quality_tradeoff_ok
        else "HOLD_W15_POLICY_REPLAY"
    )

    out_doc = {
        "schema": "track_a_week15_policy_replay_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "pack": str(args.pack),
            "w15_e1": str(args.e1),
            "w15_e2": str(args.e2),
            "w15_e3": str(args.e3),
        },
        "week15_summary": {
            "entry_decision": (pack.get("entry_condition") or {}).get("week14_decision"),
            "e1_decision": e1.get("decision"),
            "e2_decision": e2.get("decision"),
            "e3_decision": e3.get("decision"),
            "e1_viable_count": int(e1.get("viable_count", 0)),
            "e2_viable_count": int(e2.get("viable_count", 0)),
            "e3_viable_count": int(e3.get("viable_count", 0)),
        },
        "replay_checks": {
            "policy_floor": policy_floor,
            "best_saving_seen": best_saving,
            "best_jaccard_seen": best_jaccard,
            "best_integrity_seen": best_integrity,
            "policy_floor_ok": policy_floor_ok,
            "integrity_ok": integrity_ok,
            "quality_tradeoff_flag": quality_tradeoff_flag,
            "required_quality_tradeoff_flag": require_quality_tradeoff_flag,
            "quality_tradeoff_ok": quality_tradeoff_ok,
        },
        "decision": decision,
        "next_action": (
            "Keep Track A commercialization HOLD and design Week-16 hypothesis pack."
            if decision == "HOLD_W15_POLICY_REPLAY"
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
