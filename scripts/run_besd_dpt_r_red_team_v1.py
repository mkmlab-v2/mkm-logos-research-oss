#!/usr/bin/env python3
"""BESD DPT-R adversarial red-team v1 (conceptual; no theory repair)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "docs/research/besd/besd_v0_2_spec_draft_v1/BESD_V0_2_SPEC_DRAFT.md"
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
OUT_JSON = OUT_DIR / "BESD_DPT_R_RED_TEAM_V1.json"

# Spec-level safeguards (read from BESD v0.2 draft — fixed anchors for audit)
SPEC_SAFEGUARDS = {
    "agency_sovereignty_not_total_autonomy": True,
    "truth_in_pi_inputs": True,
    "context_in_pi_inputs": True,
    "t_adaptive_for_physical_constraint": True,
    "r_imposed_ne_c_constraint": True,
    "step4_context_sensitive_no_romanticize_danger": True,
    "mimetic_break_required": True,
    "forgiveness_ne_amnesia": True,
    "forgiveness_ne_trust": True,
    "historical_contestation_ceiling": True,
    "r_not_produce_g": True,
}

# Reference stub gaps (honest audit of T_DPT_v1_hypo implementation)
STUB_GAPS = {
    "pi_ignores_telos_truth_context": True,
    "domain_only_action_map": True,
    "no_abstain_on_uncertainty": True,
    "no_explicit_exit_report_legal_paths": True,
    "no_third_party_harm_check": True,
}


@dataclass
class AttackVerdict:
    case_id: str
    axis: str
    question: str
    spec_verdict: str  # HOLD | LEAK | GAP | SAFE
    impl_verdict: str
    leak_tags: list[str] = field(default_factory=list)
    safeguard_required: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class PriorArtRow:
    framework: str
    imposed_role: str
    dignity_invariant: str
    telos_control: str
    mimetic_break: str
    coercion_exposure: str
    cost_return: str
    forgiveness_ne_trust: str
    future_option: str
    formal_operator: str
    classification: str


def load_spec_text() -> str:
    if SPEC_PATH.exists():
        return SPEC_PATH.read_text(encoding="utf-8")
    return ""


def axis1_attacks() -> list[AttackVerdict]:
    """Agency Sovereignty → autonomism."""
    cases = [
        ("A1", "Telos is misperceived", ["TRUTH_CONSTRAINT_DROP"], ["truth constraint", "context constraint", "ABSTAIN under uncertainty"]),
        ("A2", "Agent uses dignity to rationalize revenge", [], ["mimetic break", "proportionality", "third-party harm"]),
        ("A3", "Truth is uncertain", ["TRUTH_CONSTRAINT_DROP"], ["uncertainty handling", "ABSTAIN"]),
        ("A4", "Religious certainty overrides evidence", ["TRUTH_CONSTRAINT_DROP", "ARBITRARY_SELF_AUTHORIZATION"], ["truth over dogmatic telos", "accountability"]),
        ("A5", "Competing legitimate authorities exist", ["ARBITRARY_SELF_AUTHORIZATION"], ["context constraint", "proportionality"]),
        ("A6", "Chosen response harms third party", ["THIRD_PARTY_HARM_BLINDNESS"], ["third-party harm constraint", "proportionality"]),
    ]
    out: list[AttackVerdict] = []
    for cid, q, leaks, safeguards in cases:
        spec_v = "GAP" if cid in {"A3", "A5", "A6"} else "HOLD"
        if cid == "A4":
            spec_v = "GAP"
        impl_v = "LEAK"
        impl_leaks = list(leaks)
        if STUB_GAPS["pi_ignores_telos_truth_context"]:
            if "TRUTH_CONSTRAINT_DROP" not in impl_leaks and cid in {"A1", "A3", "A4", "A5"}:
                impl_leaks.append("TRUTH_CONSTRAINT_DROP")
        if STUB_GAPS["no_third_party_harm_check"] and cid == "A6":
            impl_leaks.append("THIRD_PARTY_HARM_BLINDNESS")
        if cid == "A2" and STUB_GAPS["domain_only_action_map"]:
            impl_leaks.append("AUTONOMISM_LEAK")
        out.append(
            AttackVerdict(
                case_id=cid,
                axis="AXIS1_AGENCY_SOVEREIGNTY_TO_AUTONOMISM",
                question=q,
                spec_verdict=spec_v,
                impl_verdict=impl_v if impl_leaks else "HOLD",
                leak_tags=impl_leaks,
                safeguard_required=safeguards,
                notes="Spec names Truth/Context in pi; does not operationalize ABSTAIN or third-party harm. Stub ignores pi inputs.",
            )
        )
    return out


def axis2_attacks() -> list[AttackVerdict]:
    """Dignity invariance → unsafe passivity."""
    required_paths = ["EXIT", "SEEK_HELP", "REPORT", "PROTECT", "LEGAL_REMEDY", "PHYSICAL_SELF_PROTECTION_WHEN_JUSTIFIED"]
    cases = [
        ("B1", "domestic violence"),
        ("B2", "workplace abuse"),
        ("B3", "stalking"),
        ("B4", "child/vulnerable-person protection"),
        ("B5", "immediate physical threat"),
        ("B6", "coercion where withdrawal is safest"),
    ]
    out: list[AttackVerdict] = []
    spec_text = load_spec_text().lower()
    spec_lists_safety = (
        "must not romanticize danger" in spec_text
        and "context-sensitive" in spec_text
        and "t_adaptive" in spec_text.replace("-", "_")
    )
    for cid, q in cases:
        spec_v = "GAP"  # spec does not enumerate EXIT/REPORT paths in operator steps
        impl_v = "LEAK"
        leaks = ["EXIT_PATH_BLOCK", "LEGAL_REMEDY_BLOCK"] if STUB_GAPS["no_explicit_exit_report_legal_paths"] else []
        if cid in {"B5", "B6"}:
            leaks.append("PROTECTIVE_ACTION_BLOCK")
        if cid == "B1":
            leaks.append("UNSAFE_PASSIVITY")
        out.append(
            AttackVerdict(
                case_id=cid,
                axis="AXIS2_DIGNITY_TO_UNSAFE_PASSIVITY",
                question=q,
                spec_verdict=spec_v,
                impl_verdict=impl_v,
                leak_tags=leaks,
                safeguard_required=required_paths,
                notes=(
                    "Dignity invariant compatible with protective action in principle; "
                    f"spec partial safety language={spec_lists_safety}; "
                    "operator steps do not enumerate protective/exit/legal paths."
                ),
            )
        )
    return out


def prior_art_matrix() -> list[PriorArtRow]:
    dims = "imposed_role dignity telos_control mimetic_break coercion_exposure cost_return forgiveness_ne_trust future_option formal_operator".split()

    def row(
        name: str,
        vals: tuple[str, ...],
        classification: str,
    ) -> PriorArtRow:
        return PriorArtRow(name, *vals, classification=classification)

    partial = "PARTIAL_OVERLAP"
    distinct = "STRUCTURALLY_DISTINCT_CANDIDATE"
    subsumed = "SUBSUMED_BY_PRIOR"

    return [
        row(
            "Walter Wink Third Way",
            (partial, "NO", partial, partial, partial, "NO", "NO", "NO", "NO"),
            partial,
        ),
        row(
            "Strategic nonviolent resistance (Sharp/Gandhi lineage)",
            ("NO", "NO", partial, partial, partial, partial, partial, "NO", "NO"),
            partial,
        ),
        row(
            "ACT values-based action",
            ("NO", "NO", partial, "NO", "NO", "NO", "NO", "NO", "NO"),
            subsumed,
        ),
        row(
            "CBT response regulation",
            ("NO", "NO", partial, "NO", "NO", "NO", "NO", "NO", "NO"),
            subsumed,
        ),
        row(
            "Stoic response control (prohairesis)",
            ("NO", partial, partial, partial, "NO", "NO", "NO", "NO", "NO"),
            partial,
        ),
        row(
            "Reactance / autonomy theory",
            (partial, "NO", partial, "NO", "NO", "NO", "NO", "NO", partial),
            partial,
        ),
        row(
            "Self-determination theory",
            ("NO", "NO", partial, "NO", "NO", "NO", "NO", "NO", "NO"),
            subsumed,
        ),
        row(
            "Moral agency models",
            (partial, partial, partial, partial, "NO", "NO", "NO", "NO", "NO"),
            partial,
        ),
        row(
            "Generous TFT / reciprocity",
            ("NO", "NO", "NO", partial, "NO", partial, partial, partial, partial),
            partial,
        ),
        row(
            "DPT-R (proposed kernel)",
            ("YES", "YES", "YES", "YES", partial, partial, partial, partial, "YES"),
            distinct,
        ),
    ]


def ablation_tests() -> list[dict[str, Any]]:
    return [
        {
            "id": "C1",
            "remove": "Agency Sovereignty",
            "collapses_to": "reactive opponent-controlled policy / mirror retaliation loop",
            "distinctiveness_lost": True,
        },
        {
            "id": "C2",
            "remove": "Role Refusal",
            "collapses_to": "passive endurance / subordinate internalization",
            "distinctiveness_lost": True,
        },
        {
            "id": "C3",
            "remove": "Mimetic Break",
            "collapses_to": "TFT / reciprocal retaliation / CBT impulse regulation only",
            "distinctiveness_lost": True,
        },
        {
            "id": "C4",
            "remove": "Dignity Invariance",
            "collapses_to": "performance moralism / health-score dignity",
            "distinctiveness_lost": True,
        },
        {
            "id": "C5",
            "remove": "Cost Return",
            "collapses_to": "quietist nonviolence without exposure",
            "distinctiveness_lost": False,
        },
        {
            "id": "C6",
            "remove": "Future Option Value",
            "collapses_to": "scorched-earth conflict / no forgiveness-trust distinction",
            "distinctiveness_lost": False,
        },
    ]


def counterexample_tests() -> list[dict[str, Any]]:
  cases = [
        {
            "id": "X1",
            "scenario": "mirroring legally/ethically justified (self-defense)",
            "spec_allows": True,
            "spec_note": "Step 5: mirror allowed for independently justified lawful/protective reasons",
            "impl_allows": False,
            "impl_note": "Stub always selects domain-mapped non-mirror class",
            "fail_tag": "CONTEXT_SENSITIVITY_FAILURE",
        },
        {
            "id": "X2",
            "scenario": "immediate force necessary",
            "spec_allows": True,
            "spec_note": "T_adaptive + feasible action set; not romanticize danger",
            "impl_allows": False,
            "fail_tag": "PROTECTIVE_ACTION_BLOCK",
        },
        {
            "id": "X3",
            "scenario": "cooperation strategically superior",
            "spec_allows": True,
            "impl_allows": False,
            "fail_tag": "ONE_RESPONSE_FITS_ALL",
        },
        {
            "id": "X4",
            "scenario": "withdrawal superior",
            "spec_allows": True,
            "impl_allows": False,
            "fail_tag": "EXIT_PATH_BLOCK",
        },
        {
            "id": "X5",
            "scenario": "silence superior",
            "spec_allows": True,
            "impl_allows": False,
            "fail_tag": "CONTEXT_SENSITIVITY_FAILURE",
        },
        {
            "id": "X6",
            "scenario": "public exposure harms victim",
            "spec_allows": True,
            "spec_note": "Step 6 conditional, not mandatory",
            "impl_allows": True,
            "fail_tag": None,
        },
        {
            "id": "X7",
            "scenario": "telos conflicts with truth/evidence",
            "spec_allows": True,
            "spec_note": "Truth in pi; gap: no ABSTAIN rule written",
            "impl_allows": False,
            "fail_tag": "TRUTH_CONSTRAINT_DROP",
        },
        {
            "id": "X8",
            "scenario": "forgiveness inappropriate as immediate framing",
            "spec_allows": True,
            "spec_note": "forgiveness ≠ trust; step 7 preserves accountability",
            "impl_allows": True,
            "fail_tag": None,
        },
    ]
  return cases


def count_tags(attacks: list[AttackVerdict], tag: str) -> int:
    return sum(1 for a in attacks if tag in a.leak_tags)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    a1 = axis1_attacks()
    a2 = axis2_attacks()
    prior = prior_art_matrix()
    ablation = ablation_tests()
    counter = counterexample_tests()

    metrics = {
        "AUTONOMISM_LEAK_N": count_tags(a1, "AUTONOMISM_LEAK") + sum(
            1 for a in a1 if a.impl_verdict == "LEAK" and "ARBITRARY_SELF_AUTHORIZATION" in a.leak_tags
        ),
        "ARBITRARY_SELF_AUTHORIZATION_N": count_tags(a1, "ARBITRARY_SELF_AUTHORIZATION"),
        "TRUTH_CONSTRAINT_DROP_N": count_tags(a1, "TRUTH_CONSTRAINT_DROP")
        + sum(1 for c in counter if c.get("fail_tag") == "TRUTH_CONSTRAINT_DROP" and not c["impl_allows"]),
        "THIRD_PARTY_HARM_BLINDNESS_N": count_tags(a1, "THIRD_PARTY_HARM_BLINDNESS"),

        "UNSAFE_PASSIVITY_N": count_tags(a2, "UNSAFE_PASSIVITY"),
        "EXIT_PATH_BLOCK_N": count_tags(a2, "EXIT_PATH_BLOCK")
        + sum(1 for c in counter if c.get("fail_tag") == "EXIT_PATH_BLOCK"),
        "LEGAL_REMEDY_BLOCK_N": count_tags(a2, "LEGAL_REMEDY_BLOCK"),
        "PROTECTIVE_ACTION_BLOCK_N": count_tags(a2, "PROTECTIVE_ACTION_BLOCK")
        + sum(1 for c in counter if c.get("fail_tag") == "PROTECTIVE_ACTION_BLOCK"),

        "PRIOR_ART_IDENTICAL_N": sum(1 for p in prior if p.classification == "IDENTICAL"),
        "PRIOR_ART_SUBSUMED_N": sum(1 for p in prior if p.classification == "SUBSUMED_BY_PRIOR"),
        "NOVELTY_OVERCLAIM_N": 0,

        "ONE_RESPONSE_FITS_ALL_N": sum(1 for c in counter if c.get("fail_tag") == "ONE_RESPONSE_FITS_ALL"),
        "CONTEXT_SENSITIVITY_FAILURE_N": sum(
            1 for c in counter if c.get("fail_tag") == "CONTEXT_SENSITIVITY_FAILURE" and not c["impl_allows"]
        ),
        "BESD_FIREWALL_DRIFT_N": 0,
    }

    # Implementation-layer safety failures (stub); spec conceptual gaps reported separately
    impl_safety_fail = (
        metrics["UNSAFE_PASSIVITY_N"]
        + metrics["EXIT_PATH_BLOCK_N"]
        + metrics["LEGAL_REMEDY_BLOCK_N"]
        + metrics["PROTECTIVE_ACTION_BLOCK_N"]
    )

    kernel_support = {
        "imposed_role_detection": True,
        "dignity_constraint": True,
        "telos_truth_context_control": "SPEC_NOMINAL_IMPL_GAP",
        "non_mimetic_response": True,
        "ablation_C1_C4_each_distinctiveness_lost": True,
        "verdict": "MINIMAL_DISTINCTIVE_KERNEL_CANDIDATE_SPEC_LEVEL",
    }

    prior_identical = metrics["PRIOR_ART_IDENTICAL_N"]
    prior_subsumed_only = metrics["PRIOR_ART_SUBSUMED_N"] >= 3 and not any(
        p.classification == "STRUCTURALLY_DISTINCT_CANDIDATE" for p in prior if p.framework.startswith("DPT-R")
    )

    spec_axis1_gaps = sum(1 for a in a1 if a.spec_verdict == "GAP")
    spec_axis2_gaps = sum(1 for a in a2 if a.spec_verdict == "GAP")

    if prior_identical > 0:
        decide = "BESD_DPT_R_RED_TEAM_BLOCKED_PRIOR_ART_UNRESOLVED"
    elif impl_safety_fail > 0 or metrics["CONTEXT_SENSITIVITY_FAILURE_N"] > 0:
        decide = "BESD_DPT_R_RED_TEAM_PASS_WITH_MAJOR_NARROWING"
    elif spec_axis1_gaps + spec_axis2_gaps > 0:
        decide = "BESD_DPT_R_RED_TEAM_PASS_WITH_MAJOR_NARROWING"
    elif metrics["ARBITRARY_SELF_AUTHORIZATION_N"] > 0:
        decide = "BESD_DPT_R_RED_TEAM_FAIL"
    else:
        decide = "BESD_DPT_R_RED_TEAM_PASS"

    # Honest: stub impl forces narrowing
    if STUB_GAPS["domain_only_action_map"]:
        decide = "BESD_DPT_R_RED_TEAM_PASS_WITH_MAJOR_NARROWING"

    payload = {
        "schema": "besd_dpt_r_red_team_v1",
        "mission": "COMMANDER_BESD_DPT_R_RED_TEAM_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING"],
        "send_gate": "HOLD",
        "evaluation_layers": {
            "spec": str(SPEC_PATH),
            "reference_implementation": "scripts/run_besd_dpt_r_synthetic_fixture_validation_v1.py (T_DPT_v1_hypo)",
            "theory_repaired_during_attack": False,
        },
        "summary": metrics,
        "safety_metrics_target": "all safety metrics = 0 at implementation layer (not met for stub)",
        "spec_gaps": {
            "AXIS1_GAPS_N": spec_axis1_gaps,
            "AXIS2_GAPS_N": spec_axis2_gaps,
            "missing_operational_rules": [
                "ABSTAIN under truth uncertainty",
                "explicit third-party harm constraint",
                "enumerated EXIT/REPORT/LEGAL_REMEDY/PROTECT paths in operator steps",
            ],
        },
        "DPT_R_MINIMAL_DISTINCTIVE_KERNEL": kernel_support,
        "DECIDE_ONE": decide,
        "axis1_attacks": [asdict(a) for a in a1],
        "axis2_attacks": [asdict(a) for a in a2],
        "axis3_prior_art": [asdict(p) for p in prior],
        "ablation_tests": ablation,
        "counterexample_tests": counter,
        "required_safeguards_not_auto_added": [
            "truth constraint operationalization",
            "context constraint operationalization",
            "proportionality",
            "accountability",
            "third-party harm constraint",
            "uncertainty / ABSTAIN",
            "EXIT SEEK_HELP REPORT PROTECT LEGAL_REMEDY paths",
        ],
        "claim_ceiling": {
            "pass_establishes": "DPT-R survived bounded adversarial conceptual review at spec level with documented implementation gaps",
            "does_not_establish": [
                "biblical truth",
                "theological consensus",
                "historical correctness",
                "novelty",
                "efficacy",
                "superiority",
                "clinical usefulness",
                "universal optimality",
            ],
        },
        "state_pins": {
            "SYNTHETIC_INTERNAL_COHERENCE": "PASS",
            "REAL_WORLD_VALIDITY": "NOT_ESTABLISHED",
            "NOVELTY": "NOT_ESTABLISHED",
            "NEXT": "ADVERSARIAL_RED_TEAM_COMPLETE_SPEC_NARROWING_REQUIRED",
        },
        "STOP_AFTER_RESULT": True,
        "reproduce_command": "py scripts/run_besd_dpt_r_red_team_v1.py",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"DECIDE_ONE": decide, **metrics}, indent=2))
    print("OUT:", OUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
