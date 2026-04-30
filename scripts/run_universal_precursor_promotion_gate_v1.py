#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Promotion gate for universal precursor ruleset (B->A candidate).")
    ap.add_argument(
        "--ruleset-json",
        default="docs/final/artifacts/universal_precursor_ruleset_v1_latest.json",
    )
    ap.add_argument(
        "--digest-json",
        default="docs/final/artifacts/universal_precursor_cluster_digest_v1_latest.json",
    )
    ap.add_argument(
        "--sufficiency-json",
        default="docs/final/artifacts/universal_precursor_sufficiency_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_promotion_gate_v1_latest.json",
    )
    args = ap.parse_args()

    ruleset = _read_json(_resolve(args.ruleset_json))
    digest = _read_json(_resolve(args.digest_json))
    suff = _read_json(_resolve(args.sufficiency_json))

    ruleset_ok = (
        bool(ruleset.get("research_only") is True)
        and bool(ruleset.get("a_track_binding_forbidden") is True)
        and ((ruleset.get("gate") or {}).get("decision") == "GO_RESEARCH")
    )
    suff_ok = (
        (suff.get("overall_decision") == "SUFFICIENT_RESEARCH")
        and int(suff.get("pass_count") or 0) == int(suff.get("total_checks") or -1)
    )
    cluster_count = int(digest.get("cluster_count") or 0)
    cluster_floor_ok = cluster_count >= 10

    gate_checks = {
        "ruleset_research_bulkhead_ok": ruleset_ok,
        "sufficiency_all_checks_ok": suff_ok,
        "cluster_count_floor_ok": cluster_floor_ok,
    }
    pre_human_ready = all(gate_checks.values())

    # Constitution guardrail: B->A requires explicit human review.
    final_decision = "READY_FOR_HUMAN_REVIEW" if pre_human_ready else "HOLD"
    auto_promoted = False

    out_doc = {
        "schema": "universal_precursor_promotion_gate_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "ruleset_json": str(_resolve(args.ruleset_json)),
            "digest_json": str(_resolve(args.digest_json)),
            "sufficiency_json": str(_resolve(args.sufficiency_json)),
        },
        "gate_checks": gate_checks,
        "pre_human_review_ready": pre_human_ready,
        "decision": final_decision,
        "auto_promoted_to_track_a": auto_promoted,
        "required_next_action": "human_review_gate",
        "note": "Automatic Track A/live promotion is blocked by constitution; human approval required.",
    }

    out_path = _resolve(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(json.dumps({"decision": final_decision, "pre_human_review_ready": pre_human_ready}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
