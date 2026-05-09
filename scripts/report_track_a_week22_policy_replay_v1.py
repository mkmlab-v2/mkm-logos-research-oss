#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_hypothesis_pack_v1.json"
E1 = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_staged_guard_unlock_sweep_v1.json"
E2 = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e2_candidate_pool_spike_cap62_v1.json"
E3 = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_e15_router_blend_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week22_policy_replay_v1.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _doc_metrics(doc: dict[str, Any]) -> dict[str, float]:
    if "metrics" in doc and isinstance(doc["metrics"], dict):
        m = doc["metrics"]
        return {
            "saving": float(m.get("global_token_saving_rate", 0.0) or 0.0),
            "jaccard": float(m.get("avg_reconstruction_fidelity_jaccard", 0.0) or 0.0),
            "integrity": float(m.get("avg_sensitive_integrity", 0.0) or 0.0),
        }
    baseline = doc.get("baseline_router_on") or {}
    if isinstance(baseline, dict):
        return {
            "saving": float(baseline.get("global_token_saving_rate", 0.0) or 0.0),
            "jaccard": float(baseline.get("avg_reconstruction_fidelity_jaccard", 0.0) or 0.0),
            "integrity": float(baseline.get("avg_sensitive_integrity", 0.0) or 0.0),
        }
    return {"saving": 0.0, "jaccard": 0.0, "integrity": 0.0}


def _viable_flag(doc: dict[str, Any]) -> bool:
    if int(doc.get("viable_count", 0) or 0) > 0:
        return True
    gate = doc.get("gate")
    if isinstance(gate, dict) and all(bool(v) for v in gate.values()):
        return True
    decision = str(doc.get("decision", ""))
    return decision.startswith("GO_")


def _read_replay_config(pack: dict[str, Any]) -> tuple[float, bool]:
    exps = ((pack.get("pack") or {}).get("experiments") or [])
    replay_exp = next((x for x in exps if str(x.get("id")) == "W22-E4"), {})
    cfg = replay_exp.get("config") or {}
    policy_floor = float(cfg.get("policy_floor", 0.49))
    require_quality_tradeoff_flag = bool(cfg.get("require_quality_tradeoff_flag", False))
    return policy_floor, require_quality_tradeoff_flag


def main() -> int:
    ap = argparse.ArgumentParser(description="Consolidate Week-22 experiments into final policy replay decision.")
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
    policy_floor, require_quality_tradeoff_flag = _read_replay_config(pack)

    m1 = _doc_metrics(e1)
    m2 = _doc_metrics(e2)
    m3 = _doc_metrics(e3)

    best_saving = max(m1["saving"], m2["saving"], m3["saving"])
    best_jaccard = max(m1["jaccard"], m2["jaccard"], m3["jaccard"])
    best_integrity = max(m1["integrity"], m2["integrity"], m3["integrity"])

    policy_floor_ok = best_saving >= policy_floor
    integrity_ok = best_integrity >= 1.0
    quality_tradeoff_flag = not any(_viable_flag(doc) for doc in (e1, e2, e3))
    quality_tradeoff_ok = quality_tradeoff_flag == require_quality_tradeoff_flag

    decision = (
        "GO_W22_POLICY_REPLAY"
        if policy_floor_ok and integrity_ok and quality_tradeoff_ok
        else "HOLD_W22_POLICY_REPLAY"
    )

    out_doc = {
        "schema": "track_a_week22_policy_replay_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "pack": str(args.pack),
            "w22_e1": str(args.e1),
            "w22_e2": str(args.e2),
            "w22_e3": str(args.e3),
        },
        "week22_summary": {
            "entry_decision": (pack.get("entry_condition") or {}).get("week21_decision"),
            "e1_decision": e1.get("decision"),
            "e2_decision": e2.get("decision"),
            "e3_decision": e3.get("decision"),
            "e1_viable_count": int(e1.get("viable_count", 0) or 0),
            "e2_viable_count": int(e2.get("viable_count", 0) or 0),
            "e3_viable_count": int(e3.get("viable_count", 0) or 0),
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
            "Emit Track A promotion decision receipt and prepare commercialization package."
            if decision == "GO_W22_POLICY_REPLAY"
            else "Keep commercialization HOLD and continue generator-level Week-23 R&D."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
