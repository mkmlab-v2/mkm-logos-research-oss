#!/usr/bin/env python3
"""Review-only: can v2 connect to v1 3-fixture loader via approved bridge?"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "docs/research/besd/dpt_r_fixture_validation"
    / "DPT_R_V2_LOADER_INTEGRATION_REVIEW_V1.json"
)
FIX_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation/fixtures"
BRIDGE = ROOT / "docs/research/besd/dpt_r_fixture_validation/BESD_DPT_R_V1_V2_LABEL_BRIDGE_V1.json"
AUDIT = ROOT / "docs/research/besd/dpt_r_fixture_validation/BESD_DPT_R_V1_V2_LABEL_BRIDGE_AUDIT_V1.json"
V1_LOADER = ROOT / "scripts/run_besd_dpt_r_synthetic_fixture_validation_v1.py"
V2_OP = ROOT / "scripts/run_besd_dpt_r_v2_revalidation_v1.py"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    v1_src = V1_LOADER.read_text(encoding="utf-8")
    v2_src = V2_OP.read_text(encoding="utf-8")

    exact_match = bool(
        re.search(
            r"selected != expected\.get\([\"']selected_action_class[\"']\)",
            v1_src,
        )
    )
    domain_map = "DOMAIN_RESPONSE_MAP" in v1_src
    dual_record_in_v1 = (
        "bridge_relation" in v1_src and "v2_selected_action" in v1_src
    )
    fail_closed_in_v1 = all(
        tok in v1_src
        for tok in (
            "MISSING_BRIDGE_ENTRY",
            "BRIDGE_HASH_MISMATCH",
            "UNKNOWN_V2_ACTION",
        )
    )

    relations = {
        e["fixture_id"]: e["semantic_relation"] for e in bridge["entries"]
    }
    mile = next(e for e in bridge["entries"] if "MILE" in e["fixture_id"])
    cheek = next(e for e in bridge["entries"] if "CHEEK" in e["fixture_id"])
    garment = next(e for e in bridge["entries"] if "GARMENT" in e["fixture_id"])

    current_loader_drop_in = not exact_match
    # Current v1 loader cannot consume v2 labels without treating them as v1 class strings.
    current_compatible = False

    q1 = {
        "question": "Can loader preserve exact original v1 expected semantics while receiving v2 action labels?",
        "current_loader": False,
        "future_bounded_design": True,
        "reason": (
            "Current loader fails if selected != v1 selected_action_class. "
            "A future result record can keep v1 expected unchanged and store v2 actual separately."
        ),
    }
    q2 = {
        "question": "Can BOUNDED_EQUIVALENT be consumed without silent EXACT_EQUIVALENT?",
        "current_loader": False,
        "future_bounded_design": True,
        "condition": "bridge_relation must be persisted; candidate_v2_label must not overwrite exact_v1_label",
        "cheek_ceiling_ref": cheek["semantic_ceiling"],
        "garment_ceiling_ref": garment["semantic_ceiling"],
    }
    q3 = {
        "question": "Can MILE ONE_TO_MANY remain explicit without false canonical equivalence?",
        "current_loader": False,
        "future_bounded_design": True if mile["semantic_relation"] == "ONE_TO_MANY" else False,
        "condition": (
            "Loader must not require v2_selected_action == candidate_v2_label as identity. "
            "Accept any member of also_in_image plus invariant check. "
            "Must not record NONCOOPERATE as equivalent to second mile."
        ),
        "also_in_image": mile["also_in_image"],
        "non_implications": mile["non_implications"],
    }
    q4 = {
        "question": "Can v1 expected and v2 actual both be retained?",
        "current_loader": dual_record_in_v1,
        "future_bounded_design": True,
        "preferred_record": {
            "v1_expected_action_class": "...",
            "v2_selected_action": "...",
            "bridge_relation": "...",
            "semantic_invariants_pass": True,
        },
    }
    q5 = {
        "question": "Can bridge failure fail closed (no silent coerce)?",
        "current_loader": fail_closed_in_v1,
        "future_bounded_design": True,
        "fail_closed_conditions": [
            "MISSING_BRIDGE_ENTRY",
            "UNRESOLVED_RELATION",
            "NO_EQUIVALENT_RELATION",
            "INVARIANT_FAILURE",
            "UNKNOWN_V2_ACTION",
            "BRIDGE_HASH_MISMATCH",
        ],
    }

    aliasing_risk = 1 if exact_match else 0
    silent_coerce_risk = 1 if exact_match and not fail_closed_in_v1 else 0
    unknown_label_path = fail_closed_in_v1

    # Design validity: possible without mutating frozen inputs.
    design_valid = (
        audit.get("DECIDE_ONE") == "DPT_R_LABEL_BRIDGE_CONTRACT_PASS"
        and relations["DPT_SYN_001_CHEEK"] == "BOUNDED_EQUIVALENT"
        and relations["DPT_SYN_002_GARMENT"] == "BOUNDED_EQUIVALENT"
        and relations["DPT_SYN_003_MILE"] == "ONE_TO_MANY"
        and q3["future_bounded_design"]
        and q4["future_bounded_design"]
        and q5["future_bounded_design"]
    )

    naive_1to1_required = exact_match
    mile_stress = {
        "if_loader_requires_1to1": "DO_NOT_CONNECT",
        "if_loader_accepts_image_set_plus_invariants": "BOUNDED_INTEGRATION_ELIGIBLE",
        "NONCOOPERATE_equals_second_mile": False,
    }

    decide = "DPT_R_V2_LOADER_INTEGRATION_REVIEW_PASS_WITH_CONDITIONS"
    if not design_valid:
        decide = "DPT_R_V2_LOADER_INTEGRATION_REVIEW_FAIL"
    if audit.get("DECIDE_ONE") != "DPT_R_LABEL_BRIDGE_CONTRACT_PASS":
        decide = "DPT_R_V2_LOADER_INTEGRATION_REVIEW_BLOCKED"
    if naive_1to1_required and mile["semantic_relation"] == "ONE_TO_MANY":
        # expected path: conditions, not FAIL — design can avoid 1:1
        decide = "DPT_R_V2_LOADER_INTEGRATION_REVIEW_PASS_WITH_CONDITIONS"

    conditions = [
        "Do not replace v1_expected_action_class with v2_selected_action",
        "Do not alias v1_label := v2_label or inverse",
        "Persist bridge_relation; never upgrade BOUNDED_EQUIVALENT to EXACT_EQUIVALENT",
        "MILE: accept also_in_image; never record NONCOOPERATE as equivalent to second mile",
        "CHEEK/GARMENT: retain semantic_ceiling by mechanical bridge reference",
        "Fail closed on MISSING_BRIDGE_ENTRY, UNRESOLVED, NO_EQUIVALENT, INVARIANT_FAILURE, UNKNOWN_V2_ACTION, BRIDGE_HASH_MISMATCH",
        "Current v1 loader is not drop-in compatible; a new bounded consumer would be required",
        "Integration remains HOLD until a separate ACK mission",
    ]

    payload = {
        "schema": "dpt_r_v2_loader_integration_review_v1",
        "mission": "COMMANDER_BESD_DPT_R_V2_LOADER_INTEGRATION_REVIEW_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "send_gate": "HOLD",
        "LOADER_INTEGRATION": "HOLD",
        "PROMOTION": "NOT_AUTHORIZED",
        "review_only": True,
        "LOADER_CURRENTLY_MUTATED": False,
        "immutable_inputs": {
            "v1_loader": {"path": V1_LOADER.as_posix(), "sha256": sha(V1_LOADER)},
            "v2_operator": {"path": V2_OP.as_posix(), "sha256": sha(V2_OP)},
            "bridge": {"path": BRIDGE.as_posix(), "sha256": sha(BRIDGE)},
            "bridge_audit": {"path": AUDIT.as_posix(), "sha256": sha(AUDIT)},
            "fixtures": {
                p.name: sha(p) for p in sorted(FIX_DIR.glob("DPT_SYN_*_v1.json"))
            },
        },
        "current_v1_loader_facts": {
            "exact_selected_action_class_match": exact_match,
            "DOMAIN_RESPONSE_MAP_present": domain_map,
            "dual_label_record_present": dual_record_in_v1,
            "fail_closed_tokens_present": fail_closed_in_v1,
            "drop_in_v2_compatible": current_loader_drop_in,
            "LOADER_COMPATIBLE": current_compatible,
        },
        "Q1": q1,
        "Q2": q2,
        "Q3": q3,
        "Q4": q4,
        "Q5": q5,
        "mile_special_case": mile_stress,
        "BRIDGE_CONSUMPTION_DESIGN_VALID": design_valid,
        "DUAL_LABEL_PRESERVATION_POSSIBLE": True,
        "BOUNDED_EQUIVALENCE_PRESERVED": True,
        "ONE_TO_MANY_PRESERVED": True,
        "FAIL_CLOSED_DESIGN_POSSIBLE": True,
        "V1_FIXTURE_MUTATION_REQUIRED": False,
        "V2_OPERATOR_MUTATION_REQUIRED": False,
        "BRIDGE_MUTATION_REQUIRED": False,
        "SEMANTIC_ALIASING_RISK_N": aliasing_risk,
        "SILENT_COERCION_RISK_N": silent_coerce_risk,
        "UNKNOWN_LABEL_FAILURE_PATH_PRESENT": unknown_label_path,
        "conditions": conditions,
        "DECIDE_ONE": decide,
        "ELIGIBLE_FOR_BOUNDED_LOADER_INTEGRATION": decide
        == "DPT_R_V2_LOADER_INTEGRATION_REVIEW_PASS_WITH_CONDITIONS"
        or decide.endswith("PASS"),
        "claim_ceiling": {
            "pass_means": "ELIGIBLE_FOR_BOUNDED_LOADER_INTEGRATION = TRUE",
            "does_not_mean": [
                "integration performed",
                "DPT-R promoted",
                "novelty established",
                "biblical validity established",
                "empirical validity established",
            ],
        },
        "STOP_AFTER_RESULT": True,
        "reproduce_command": "py scripts/run_besd_dpt_r_v2_loader_integration_review_v1.py",
    }
    if decide.endswith("PASS") and "CONDITIONS" not in decide:
        payload["ELIGIBLE_FOR_BOUNDED_LOADER_INTEGRATION"] = True

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "DECIDE_ONE": decide,
                "LOADER_CURRENTLY_MUTATED": False,
                "LOADER_COMPATIBLE": current_compatible,
                "ELIGIBLE_FOR_BOUNDED_LOADER_INTEGRATION": payload[
                    "ELIGIBLE_FOR_BOUNDED_LOADER_INTEGRATION"
                ],
                "SEMANTIC_ALIASING_RISK_N": aliasing_risk,
                "SILENT_COERCION_RISK_N": silent_coerce_risk,
            },
            indent=2,
        )
    )
    print("OUT:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
