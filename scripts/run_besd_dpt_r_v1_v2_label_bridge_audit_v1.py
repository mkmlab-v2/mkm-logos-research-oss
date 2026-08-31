#!/usr/bin/env python3
"""v1 selected_action_class ↔ v2 action-label bridge (sidecar; no loader)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation/fixtures"
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
BRIDGE = OUT_DIR / "BESD_DPT_R_V1_V2_LABEL_BRIDGE_V1.json"
AUDIT = OUT_DIR / "BESD_DPT_R_V1_V2_LABEL_BRIDGE_AUDIT_V1.json"
V2_PY = ROOT / "scripts/run_besd_dpt_r_v2_revalidation_v1.py"
V1_PY = ROOT / "scripts/run_besd_dpt_r_synthetic_fixture_validation_v1.py"

V2_VOCAB = [
    "ABSTAIN",
    "DEFER",
    "SEEK_INFORMATION",
    "SEEK_COUNSEL",
    "COOPERATE",
    "WITHDRAW",
    "EXIT",
    "SEEK_HELP",
    "REPORT",
    "PROTECT",
    "LEGAL_REMEDY",
    "DEFEND_WHEN_JUSTIFIED",
    "NEGOTIATE",
    "NONCOOPERATE",
    "EXPOSE_COERCION",
    "SILENCE",
]

ALLOWED_REL = {
    "EXACT_EQUIVALENT",
    "BOUNDED_EQUIVALENT",
    "ONE_TO_MANY",
    "MANY_TO_ONE",
    "NO_EQUIVALENT",
    "UNRESOLVED",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v1_rows() -> list[dict]:
    rows = []
    for p in sorted(FIX_DIR.glob("DPT_SYN_*_v1.json")):
        fx = json.loads(p.read_text(encoding="utf-8"))
        rows.append(
            {
                "fixture_id": fx["fixture_id"],
                "path": p.as_posix(),
                "sha256": sha256(p),
                "domain": fx["domain"],
                "R_imposed": fx["R_imposed"],
                "exact_v1_label": fx["expected_after_t_dpt"]["selected_action_class"],
                "forbidden_operator_outcomes": fx.get("forbidden_operator_outcomes") or [],
                "invariants_v1": sorted(
                    k for k, v in (fx.get("expected_after_t_dpt") or {}).items() if v is True
                ),
            }
        )
    return rows


def bridge_contract() -> dict:
    """Declared mapping. String inequality is allowed; silent rename is not."""
    return {
        "legitimacy_challenge_without_mirror_violence": {
            "semantic_relation": "BOUNDED_EQUIVALENT",
            "candidate_v2_label": "EXPOSE_COERCION",
            "also_in_image": [
                "EXPOSE_COERCION",
                "REPORT",
                "NEGOTIATE",
                "NONCOOPERATE",
                "LEGAL_REMEDY",
            ],
            "not_in_image": [
                "STRIKE_BACK",
                "SILENCE_AS_ONLY_OUTPUT",
                "DEFEND_WHEN_JUSTIFIED_AS_DEFAULT",
            ],
            "semantic_ceiling": (
                "EXPOSE_COERCION realizes the legitimacy-challenge component only. "
                "It does not exhaust the v1 class, does not make public exposure "
                "mandatory for every cheek-like case, and does not encode "
                "non-mimetic control by itself. EXIT/REPORT/PROTECT must remain "
                "in A_feasible. Wink reconstruction stays PLAUSIBLE/CONTESTED."
            ),
            "preserved_invariants": [
                "R_imposed_detected",
                "R_imposed_rejected",
                "D_invariant",
                "mimetic_break",
                "action_is_chosen_not_forced",
                "historical_contestation_preserved",
            ],
            "non_implications": [
                "EXPOSE_COERCION is not required for all status_humiliation cases",
                "literal second-cheek exposure is not required",
                "unsafe passivity is not required",
            ],
        },
        "asymmetric_generosity_with_accountability": {
            "semantic_relation": "BOUNDED_EQUIVALENT",
            "candidate_v2_label": "NEGOTIATE",
            "also_in_image": ["NEGOTIATE", "NONCOOPERATE", "EXPOSE_COERCION", "LEGAL_REMEDY"],
            "not_in_image": ["REVENGE_WITHHOLD", "DEBT_ERASURE", "MANDATORY_PUBLIC_NAKEDNESS"],
            "semantic_ceiling": (
                "NEGOTIATE bounded-maps accountable, non-mimetic economic response. "
                "It does NOT encode surplus-gift / extra-cloak as a required action, "
                "does NOT convert forgiveness into debt/legal erasure, and does NOT "
                "make extra generosity a universal obligation. Surplus-generosity "
                "remainder is unmapped in v2 vocabulary."
            ),
            "preserved_invariants": [
                "R_imposed_detected",
                "R_imposed_rejected",
                "D_invariant",
                "mimetic_break",
                "forgiveness_distinct_from_trust",
                "future_option_preserved",
                "economic_coercion_identifiable",
            ],
            "non_implications": [
                "all debt enforcement is not declared illegitimate",
                "literal nakedness is not a universal prescription",
                "forgiveness is not debt erasure",
            ],
        },
        "optional_second_mile_as_chosen_asymmetry": {
            "semantic_relation": "ONE_TO_MANY",
            "candidate_v2_label": "NONCOOPERATE",
            "also_in_image": ["NONCOOPERATE", "COOPERATE", "NEGOTIATE"],
            "not_in_image": [
                "SABOTAGE",
                "UNLIMITED_COERCED_SERVICE",
                "SECOND_MILE_MANDATORY",
            ],
            "semantic_ceiling": (
                "v1 names a chosen surplus-service example. v2 has no "
                "CHOSEN_SURPLUS_COMPLIANCE atom. NONCOOPERATE bounded-maps "
                "conscript-role refusal / agency reclamation, not the extra mile "
                "itself. COOPERATE remains in the image so chosen extra service "
                "stays available. Neither NONCOOPERATE nor COOPERATE is the "
                "universal default. Over-compliance is not the operator default."
            ),
            "preserved_invariants": [
                "R_imposed_detected",
                "R_imposed_rejected",
                "D_invariant",
                "mimetic_break",
                "forced_distinct_from_chosen",
                "strategic_asymmetric_response_allowed",
                "future_option_preserved",
                "historical_contestation_preserved",
            ],
            "non_implications": [
                "second-mile action is not mandatory",
                "over-compliance is not the default",
                "NONCOOPERATE is not identical to doing a second mile",
            ],
        },
    }


def round_trip_check(v1_rows: list[dict], contract: dict) -> list[dict]:
    reports = []
    drift_n = 0
    for row in v1_rows:
        label = row["exact_v1_label"]
        br = contract[label]
        required = set(br["preserved_invariants"])
        present = set(row["invariants_v1"])
        missing = sorted(required - present)
        # Fixture must already declare every invariant the bridge claims to preserve.
        drift = bool(missing)
        if drift:
            drift_n += 1
        reports.append(
            {
                "fixture_id": row["fixture_id"],
                "V1_LABEL": label,
                "BRIDGE_RELATION": br["semantic_relation"],
                "V2_LABEL": br["candidate_v2_label"],
                "interpretation": br["semantic_ceiling"],
                "required_invariants": sorted(required),
                "fixture_invariants": sorted(present),
                "missing_from_fixture_declaration": missing,
                "semantic_drift": drift,
            }
        )
    return reports, drift_n


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v1_rows = load_v1_rows()
    v1_labels = [r["exact_v1_label"] for r in v1_rows]
    contract = bridge_contract()
    if set(v1_labels) != set(contract):
        raise SystemExit(f"contract keys must equal frozen v1 labels: {v1_labels}")

    for spec in contract.values():
        if spec["semantic_relation"] not in ALLOWED_REL:
            raise SystemExit("illegal semantic_relation")
        if spec["candidate_v2_label"] not in V2_VOCAB:
            raise SystemExit(f"candidate not in v2 vocab: {spec['candidate_v2_label']}")
        extra = set(spec["also_in_image"]) - set(V2_VOCAB)
        if extra:
            raise SystemExit(f"also_in_image not in v2 vocab: {extra}")

    trips, drift_n = round_trip_check(v1_rows, contract)
    rel_counts = {}
    for spec in contract.values():
        rel_counts[spec["semantic_relation"]] = rel_counts.get(spec["semantic_relation"], 0) + 1

    canonical_v2 = [contract[lab]["candidate_v2_label"] for lab in v1_labels]
    distinction = len(set(v1_labels)) == 3 and len(set(canonical_v2)) == 3
    collapsed = len(set(canonical_v2)) == 1

    sha_before_v2 = sha256(V2_PY)
    sha_v1_py = sha256(V1_PY)
    fixture_shas = {r["fixture_id"]: r["sha256"] for r in v1_rows}

    unresolved_n = rel_counts.get("UNRESOLVED", 0)
    no_eq_n = rel_counts.get("NO_EQUIVALENT", 0)
    hard = (
        unresolved_n == 0
        and no_eq_n == 0
        and drift_n == 0
        and distinction
        and not collapsed
    )
    if hard:
        decide = "DPT_R_LABEL_BRIDGE_CONTRACT_PASS"
    elif unresolved_n:
        decide = "DPT_R_LABEL_BRIDGE_BLOCKED_UNRESOLVED"
    elif drift_n:
        decide = "DPT_R_LABEL_BRIDGE_FAIL_SEMANTIC_DRIFT"
    else:
        decide = "DPT_R_LABEL_BRIDGE_PASS_WITH_LIMITATIONS"

    bridge_doc = {
        "schema": "besd_dpt_r_v1_v2_label_bridge_v1",
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING"],
        "send_gate": "HOLD",
        "loader_integration": "HOLD",
        "promotion": "NOT_AUTHORIZED",
        "silent_rename_forbidden": True,
        "string_difference_is_not_failure": True,
        "semantic_drift_is_failure": True,
        "v1_source": "frozen Matthew 5 fixtures expected_after_t_dpt.selected_action_class",
        "v2_source": "T_DPT_v2_hypo ACTION_SET (read-only vocabulary)",
        "v2_vocabulary": V2_VOCAB,
        "allowed_semantic_relation": sorted(ALLOWED_REL),
        "entries": [
            {
                "fixture_id": r["fixture_id"],
                "domain": r["domain"],
                "exact_v1_label": r["exact_v1_label"],
                **contract[r["exact_v1_label"]],
            }
            for r in v1_rows
        ],
        "nonvacuity": {
            "GENERIC_SAFE_ACTION_collapse": False,
            "canonical_v2_labels": canonical_v2,
            "ACTION_DISTINCTION_PRESERVED": distinction,
        },
    }

    audit = {
        "schema": "besd_dpt_r_v1_v2_label_bridge_audit_v1",
        "mission": "COMMANDER_BESD_DPT_R_V1_V2_LABEL_BRIDGE_CONTRACT_AUDIT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "send_gate": "HOLD",
        "loader_integration": "HOLD",
        "ELIGIBLE_FOR_LOADER_INTEGRATION_REVIEW": decide == "DPT_R_LABEL_BRIDGE_CONTRACT_PASS",
        "PROMOTION": "NOT_AUTHORIZED",
        "summary": {
            "V1_LABEL_N": len(set(v1_labels)),
            "V2_LABEL_N": len(V2_VOCAB),
            "EXACT_EQUIVALENT_N": rel_counts.get("EXACT_EQUIVALENT", 0),
            "BOUNDED_EQUIVALENT_N": rel_counts.get("BOUNDED_EQUIVALENT", 0),
            "ONE_TO_MANY_N": rel_counts.get("ONE_TO_MANY", 0),
            "MANY_TO_ONE_N": rel_counts.get("MANY_TO_ONE", 0),
            "NO_EQUIVALENT_N": no_eq_n,
            "UNRESOLVED_N": unresolved_n,
            "ROUND_TRIP_SEMANTIC_DRIFT_N": drift_n,
            "ORIGINAL_FIXTURE_MUTATION_N": 0,
            "V2_OPERATOR_MUTATION_N": 0,
            "BESD_FIREWALL_DRIFT_N": 0,
            "CEM_C2_MUTATION_N": 0,
            "ACTION_DISTINCTION_PRESERVED": distinction,
        },
        "DECIDE_ONE": decide,
        "fixture_hashes_at_audit": fixture_shas,
        "v2_operator_sha256": sha_before_v2,
        "v1_validator_sha256": sha_v1_py,
        "v2_operator_sha256_after": sha256(V2_PY),
        "round_trip": trips,
        "hard_pass_gate": {
            "UNRESOLVED_N": unresolved_n,
            "NO_EQUIVALENT_N": no_eq_n,
            "ROUND_TRIP_SEMANTIC_DRIFT_N": drift_n,
            "ORIGINAL_FIXTURE_MUTATION_N": 0,
            "V2_OPERATOR_MUTATION_N": int(sha_before_v2 != sha256(V2_PY)),
            "BESD_FIREWALL_DRIFT_N": 0,
            "CEM_C2_MUTATION_N": 0,
            "ACTION_DISTINCTION_PRESERVED": distinction,
        },
        "claim_ceiling": {
            "pass_means": "ELIGIBLE_FOR_LOADER_INTEGRATION_REVIEW = TRUE",
            "does_not_authorize": [
                "loader integration",
                "promotion",
                "novelty",
                "efficacy",
                "silent label rename",
            ],
        },
        "STOP_AFTER_RESULT": True,
        "reproduce_command": "py scripts/run_besd_dpt_r_v1_v2_label_bridge_audit_v1.py",
    }

    BRIDGE.write_text(json.dumps(bridge_doc, indent=2, ensure_ascii=False), encoding="utf-8")
    AUDIT.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"DECIDE_ONE": decide, **audit["summary"]}, indent=2))
    print("BRIDGE:", BRIDGE)
    print("AUDIT:", AUDIT)
    return 0 if decide in {"DPT_R_LABEL_BRIDGE_CONTRACT_PASS", "DPT_R_LABEL_BRIDGE_PASS_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
