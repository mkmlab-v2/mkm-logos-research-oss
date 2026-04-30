#!/usr/bin/env python3
"""Lock manual promotion decision for universal precursor ruleset."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE = ART / "universal_precursor_promotion_gate_v1_latest.json"
DEFAULT_SUFF = ART / "universal_precursor_sufficiency_v1_latest.json"
DEFAULT_RULESET = ART / "universal_precursor_ruleset_v1_latest.json"
DEFAULT_DIGEST = ART / "universal_precursor_cluster_digest_v1_latest.json"
DEFAULT_OUT = ART / "universal_precursor_manual_promotion_decision_lock_v1_latest.json"
DEFAULT_TRACKA = ART / "universal_precursor_track_a_candidate_v1_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--promotion-gate", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--sufficiency", type=Path, default=DEFAULT_SUFF)
    ap.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    ap.add_argument("--digest", type=Path, default=DEFAULT_DIGEST)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision-note", default="manual approval granted by user")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tracka-candidate-out", type=Path, default=DEFAULT_TRACKA)
    args = ap.parse_args()

    gate = _read_json(args.promotion_gate)
    suff = _read_json(args.sufficiency)
    ruleset = _read_json(args.ruleset)
    digest = _read_json(args.digest)

    checklist = {
        "promotion_gate_ready_for_human_review": str(gate.get("decision") or "") == "READY_FOR_HUMAN_REVIEW",
        "promotion_gate_pre_human_review_ready": bool(gate.get("pre_human_review_ready")),
        "sufficiency_decision_ok": str(suff.get("overall_decision") or "") == "SUFFICIENT_RESEARCH",
        "ruleset_research_bulkhead_ok": bool(ruleset.get("research_only") is True)
        and bool(ruleset.get("a_track_binding_forbidden") is True),
        "digest_cluster_count_gte_10": int(digest.get("cluster_count") or 0) >= 10,
    }
    approved = all(checklist.values())

    lock_doc = {
        "schema": "universal_precursor_manual_promotion_decision_lock_v1",
        "locked_at_utc": _now(),
        "inputs": {
            "promotion_gate": str(args.promotion_gate.resolve()),
            "sufficiency": str(args.sufficiency.resolve()),
            "ruleset": str(args.ruleset.resolve()),
            "digest": str(args.digest.resolve()),
        },
        "review_snapshot": {
            "promotion_gate_decision": gate.get("decision"),
            "sufficiency_decision": suff.get("overall_decision"),
            "cluster_count": digest.get("cluster_count"),
            "checklist": checklist,
        },
        "final_decision": "approved" if approved else "rejected",
        "reviewer": args.reviewer,
        "decision_note": args.decision_note,
        "constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
            "a_track_candidate_only": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(lock_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if approved:
        strict_gate = suff.get("strict_gate") if isinstance(suff.get("strict_gate"), dict) else {}
        candidate = {
            "schema": "universal_precursor_track_a_candidate_v1",
            "generated_at_utc": _now(),
            "status": "APPROVED_CANDIDATE",
            "source_track": "B",
            "promotion_mode": "human_approved_candidate_only",
            "candidate_gate": {
                "min_cluster_size": strict_gate.get("min_cluster_size"),
                "min_coherence_0_1": strict_gate.get("min_coherence_0_1"),
                "min_clusters_required": strict_gate.get("min_clusters_required"),
            },
            "candidate_metrics": {
                "cluster_count": digest.get("cluster_count"),
                "sufficiency_pass_count": suff.get("pass_count"),
                "sufficiency_total_checks": suff.get("total_checks"),
            },
            "runtime_constraints": {
                "track_b_to_a_auto_bridge": False,
                "live_trigger_auto_enabled": False,
                "requires_human_review_each_release": True,
            },
            "evidence": {
                "manual_lock": str(args.out.resolve()),
                "promotion_gate": str(args.promotion_gate.resolve()),
                "sufficiency": str(args.sufficiency.resolve()),
                "ruleset": str(args.ruleset.resolve()),
            },
        }
        args.tracka_candidate_out.parent.mkdir(parents=True, exist_ok=True)
        args.tracka_candidate_out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.tracka_candidate_out}")

    print(f"WROTE: {args.out}")
    print(f"final_decision={lock_doc['final_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
