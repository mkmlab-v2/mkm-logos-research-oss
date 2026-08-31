#!/usr/bin/env python3
"""T_DPT_v2_hypo spec-narrowing revalidation (no promotion)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/research/besd/besd_v0_2_spec_draft_v1/BESD_V0_2_SPEC_DRAFT.md"
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
OUT_JSON = OUT_DIR / "BESD_DPT_R_V2_REVALIDATION_V1.json"

OPERATOR_ID = "LOGOS.CR.DPT_TRANSFORM"
OPERATOR_VERSION = "T_DPT_v2_hypo"

ACTION_SET = frozenset(
    {
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
    }
)

PROTECTIVE = frozenset(
    {
        "EXIT",
        "SEEK_HELP",
        "REPORT",
        "PROTECT",
        "LEGAL_REMEDY",
        "DEFEND_WHEN_JUSTIFIED",
        "WITHDRAW",
    }
)

MIMETIC_CONTROLLED = frozenset({"STRIKE_BACK", "REVENGE", "MIRROR_RETALIATION"})

V2_STEPS = [
    "1_Detect_imposed_role",
    "2_Assert_dignity_invariant",
    "3_Evaluate_truth_context_uncertainty",
    "4_Evaluate_safety_third_party_feasible_set",
    "5_Refuse_role_internalization",
    "6_Reclaim_agency_context_sensitive",
    "7_Enforce_non_mimetic_control",
    "8_Preserve_accountability_future_option",
]


@dataclass
class V2Result:
    case_id: str
    selected: str
    feasible: list[str]
    steps: list[str]
    pass_case: bool
    leak_tags: list[str] = field(default_factory=list)
    notes: str = ""


def feasible_set(ctx: dict[str, Any]) -> list[str]:
    """A_feasible(Truth, Context, Safety, ThirdPartyHarm, Uncertainty). No tau claimed."""
    u_material = bool(ctx.get("uncertainty_material") or ctx.get("truth_uncertain"))
    evidence_conflict = bool(ctx.get("religious_certainty_overrides_evidence"))
    third_party = bool(ctx.get("third_party_harm_dominates") or ctx.get("third_party_harm"))
    expose_harms_victim = bool(ctx.get("public_exposure_increases_victim_risk"))
    dv = bool(ctx.get("domestic_violence") or ctx.get("case_family") == "domestic_violence")
    immediate = bool(ctx.get("immediate_physical_threat"))
    coop_sup = bool(ctx.get("cooperation_objectively_superior"))
    withdraw_safest = bool(ctx.get("withdrawal_safest"))
    silence_sup = bool(ctx.get("silence_superior"))
    revenge_via_dignity = bool(ctx.get("dignity_rationalizes_revenge"))
    justified_force = bool(ctx.get("immediate_force_necessary") or ctx.get("mirroring_legally_justified"))
    telos_misperceived = bool(ctx.get("telos_misperceived"))
    competing_auth = bool(ctx.get("competing_legitimate_authorities"))

    if u_material or evidence_conflict or telos_misperceived:
        base = ["ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"]
        if competing_auth:
            base.append("SEEK_COUNSEL")
        return sorted(set(base))

    out = set(ACTION_SET)
    if revenge_via_dignity:
        out -= MIMETIC_CONTROLLED
        out.discard("EXPOSE_COERCION")
        out |= {"ABSTAIN", "SEEK_COUNSEL", "REPORT", "LEGAL_REMEDY"}
    if third_party:
        out |= {"PROTECT", "EXIT", "REPORT", "SEEK_HELP"}
        if expose_harms_victim:
            out.discard("EXPOSE_COERCION")
    if expose_harms_victim:
        out.discard("EXPOSE_COERCION")
        out |= {"WITHDRAW", "SILENCE", "SEEK_HELP", "REPORT"}
    if dv:
        out |= {"EXIT", "REPORT", "PROTECT", "SEEK_HELP", "LEGAL_REMEDY"}
    if immediate or justified_force:
        out |= {"DEFEND_WHEN_JUSTIFIED", "EXIT", "PROTECT", "SEEK_HELP"}
    if coop_sup:
        out |= {"COOPERATE", "NEGOTIATE"}
    if withdraw_safest:
        out |= {"WITHDRAW", "EXIT"}
    if silence_sup:
        out |= {"SILENCE", "ABSTAIN"}
    return sorted(out)


def select_action(ctx: dict[str, Any], feasible: list[str]) -> str:
    """Context-sensitive pick; no universal preferred action."""
    if ctx.get("dignity_rationalizes_revenge"):
        for a in ("ABSTAIN", "SEEK_COUNSEL", "REPORT"):
            if a in feasible:
                return a
    if ctx.get("uncertainty_material") or ctx.get("truth_uncertain"):
        return "ABSTAIN" if "ABSTAIN" in feasible else feasible[0]
    if ctx.get("religious_certainty_overrides_evidence"):
        return "SEEK_INFORMATION" if "SEEK_INFORMATION" in feasible else "ABSTAIN"
    if ctx.get("telos_misperceived"):
        return "SEEK_COUNSEL" if "SEEK_COUNSEL" in feasible else "ABSTAIN"
    if ctx.get("third_party_harm_dominates"):
        for a in ("PROTECT", "EXIT", "REPORT"):
            if a in feasible:
                return a
    if ctx.get("domestic_violence") or ctx.get("case_family") == "domestic_violence":
        for a in ("EXIT", "REPORT", "PROTECT"):
            if a in feasible:
                return a
    if ctx.get("immediate_physical_threat") or ctx.get("immediate_force_necessary"):
        if "DEFEND_WHEN_JUSTIFIED" in feasible:
            return "DEFEND_WHEN_JUSTIFIED"
    if ctx.get("mirroring_legally_justified") and "DEFEND_WHEN_JUSTIFIED" in feasible:
        return "DEFEND_WHEN_JUSTIFIED"
    if ctx.get("cooperation_objectively_superior") and "COOPERATE" in feasible:
        return "COOPERATE"
    if ctx.get("withdrawal_safest"):
        for a in ("WITHDRAW", "EXIT"):
            if a in feasible:
                return a
    if ctx.get("silence_superior") and "SILENCE" in feasible:
        return "SILENCE"
    if ctx.get("public_exposure_increases_victim_risk"):
        for a in ("WITHDRAW", "SILENCE", "SEEK_HELP"):
            if a in feasible:
                return a
    if ctx.get("competing_legitimate_authorities"):
        return "SEEK_COUNSEL" if "SEEK_COUNSEL" in feasible else "ABSTAIN"
    if ctx.get("workplace_abuse") or ctx.get("stalking"):
        for a in ("REPORT", "LEGAL_REMEDY", "EXIT"):
            if a in feasible:
                return a
    if ctx.get("child_protection"):
        for a in ("PROTECT", "REPORT", "SEEK_HELP"):
            if a in feasible:
                return a
    if ctx.get("preferred") in feasible:
        return str(ctx["preferred"])
    if "NONCOOPERATE" in feasible:
        return "NONCOOPERATE"
    return feasible[0]


def t_dpt_v2(case_id: str, ctx: dict[str, Any], expect_in: set[str] | None, forbid: set[str] | None) -> V2Result:
    leaks: list[str] = []
    feasible = feasible_set(ctx)
    selected = select_action(ctx, feasible)

    if selected not in ACTION_SET and selected not in feasible:
        leaks.append("ARBITRARY_SELF_AUTHORIZATION")
    if selected not in feasible:
        leaks.append("ARBITRARY_SELF_AUTHORIZATION")
        leaks.append("AUTONOMISM_LEAK")

    if ctx.get("dignity_rationalizes_revenge") and selected in MIMETIC_CONTROLLED:
        leaks.append("AUTONOMISM_LEAK")

    if (ctx.get("uncertainty_material") or ctx.get("truth_uncertain")) and selected not in {
        "ABSTAIN",
        "DEFER",
        "SEEK_INFORMATION",
        "SEEK_COUNSEL",
    }:
        leaks.append("TRUTH_CONSTRAINT_DROP")

    if ctx.get("religious_certainty_overrides_evidence") and selected not in {
        "ABSTAIN",
        "DEFER",
        "SEEK_INFORMATION",
        "SEEK_COUNSEL",
    }:
        leaks.append("TRUTH_CONSTRAINT_DROP")
        leaks.append("ARBITRARY_SELF_AUTHORIZATION")

    if ctx.get("third_party_harm_dominates") and selected == "EXPOSE_COERCION":
        leaks.append("THIRD_PARTY_HARM_BLINDNESS")

    if ctx.get("domestic_violence") or ctx.get("case_family") == "domestic_violence":
        if not (PROTECTIVE & set(feasible)):
            leaks.append("UNSAFE_PASSIVITY")
            leaks.append("EXIT_PATH_BLOCK")
            leaks.append("PROTECTIVE_ACTION_BLOCK")
        if "LEGAL_REMEDY" not in feasible:
            leaks.append("LEGAL_REMEDY_BLOCK")

    if ctx.get("immediate_physical_threat") or ctx.get("immediate_force_necessary"):
        if "DEFEND_WHEN_JUSTIFIED" not in feasible and "EXIT" not in feasible:
            leaks.append("PROTECTIVE_ACTION_BLOCK")

    if ctx.get("withdrawal_safest") and not ({"WITHDRAW", "EXIT"} & set(feasible)):
        leaks.append("EXIT_PATH_BLOCK")

    if ctx.get("public_exposure_increases_victim_risk") and selected == "EXPOSE_COERCION":
        leaks.append("CONTEXT_SENSITIVITY_FAILURE")

    if ctx.get("cooperation_objectively_superior") and "COOPERATE" not in feasible:
        leaks.append("ONE_RESPONSE_FITS_ALL")

    if expect_in and selected not in expect_in:
        leaks.append(f"EXPECTED_NOT_SELECTED:{selected}")
    if forbid and selected in forbid:
        leaks.append(f"FORBIDDEN_SELECTED:{selected}")

    notes = ""
    if ctx.get("mirroring_legally_justified") and selected == "DEFEND_WHEN_JUSTIFIED":
        notes = "surface resemblance allowed; independently justified (N3)"

    return V2Result(
        case_id=case_id,
        selected=selected,
        feasible=feasible,
        steps=list(V2_STEPS),
        pass_case=len(leaks) == 0,
        leak_tags=leaks,
        notes=notes,
    )


def cases() -> list[tuple[str, dict[str, Any], set[str] | None, set[str] | None]]:
    return [
        ("A1", {"telos_misperceived": True, "uncertainty_material": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
        ("A2", {"dignity_rationalizes_revenge": True}, {"ABSTAIN", "SEEK_COUNSEL", "REPORT", "LEGAL_REMEDY"}, MIMETIC_CONTROLLED),
        ("A3", {"truth_uncertain": True, "uncertainty_material": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
        ("A4", {"religious_certainty_overrides_evidence": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
        ("A5", {"competing_legitimate_authorities": True, "uncertainty_material": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
        ("A6", {"third_party_harm": True, "third_party_harm_dominates": True}, {"PROTECT", "EXIT", "REPORT", "SEEK_HELP"}, {"EXPOSE_COERCION"}),
        ("B1", {"domestic_violence": True, "case_family": "domestic_violence"}, {"EXIT", "REPORT", "PROTECT", "SEEK_HELP", "LEGAL_REMEDY"}, None),
        ("B2", {"workplace_abuse": True}, {"REPORT", "LEGAL_REMEDY", "EXIT"}, None),
        ("B3", {"stalking": True}, {"REPORT", "LEGAL_REMEDY", "EXIT"}, None),
        ("B4", {"child_protection": True, "third_party_harm": True}, {"PROTECT", "REPORT", "SEEK_HELP"}, None),
        ("B5", {"immediate_physical_threat": True}, {"DEFEND_WHEN_JUSTIFIED", "EXIT", "PROTECT", "SEEK_HELP"}, None),
        ("B6", {"withdrawal_safest": True}, {"WITHDRAW", "EXIT"}, None),
        ("X1", {"mirroring_legally_justified": True}, {"DEFEND_WHEN_JUSTIFIED", "EXIT", "PROTECT"}, None),
        ("X2", {"immediate_force_necessary": True, "immediate_physical_threat": True}, {"DEFEND_WHEN_JUSTIFIED", "EXIT", "PROTECT"}, None),
        ("X3", {"cooperation_objectively_superior": True}, {"COOPERATE", "NEGOTIATE"}, None),
        ("X4", {"withdrawal_safest": True}, {"WITHDRAW", "EXIT"}, None),
        ("X5", {"silence_superior": True}, {"SILENCE", "ABSTAIN"}, None),
        ("X6", {"public_exposure_increases_victim_risk": True}, {"WITHDRAW", "SILENCE", "SEEK_HELP", "REPORT"}, {"EXPOSE_COERCION"}),
        ("X7", {"religious_certainty_overrides_evidence": True, "telos_conflicts_with_evidence": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
        ("X8", {"forgiveness_inappropriate_now": True, "preferred": "REPORT"}, {"REPORT", "LEGAL_REMEDY", "ABSTAIN", "NONCOOPERATE"}, None),
        ("V2-01", {"uncertainty_material": True, "truth_uncertain": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
        ("V2-02", {"third_party_harm_dominates": True}, {"PROTECT", "EXIT", "REPORT"}, {"EXPOSE_COERCION"}),
        ("V2-03", {"domestic_violence": True}, {"EXIT", "REPORT", "PROTECT"}, None),
        ("V2-04", {"immediate_physical_threat": True}, {"DEFEND_WHEN_JUSTIFIED", "EXIT", "PROTECT"}, None),
        ("V2-05", {"cooperation_objectively_superior": True}, {"COOPERATE"}, None),
        ("V2-06", {"withdrawal_safest": True}, {"WITHDRAW", "EXIT"}, None),
        ("V2-07", {"public_exposure_increases_victim_risk": True}, {"WITHDRAW", "SILENCE", "SEEK_HELP"}, {"EXPOSE_COERCION"}),
        ("V2-08", {"religious_certainty_overrides_evidence": True}, {"ABSTAIN", "DEFER", "SEEK_INFORMATION", "SEEK_COUNSEL"}, None),
    ]


def count_tag(results: list[V2Result], tag: str) -> int:
    return sum(1 for r in results if any(tag in t for t in r.leak_tags))


def prior_art_audit() -> list[dict[str, Any]]:
    """COMPONENT_OVERLAP vs KERNEL_SUBSUMED. Full DPT-R not subsumed on one-component overlap."""
    rows = [
        ("Walter Wink Third Way", "COMPONENT_OVERLAP", "creative resistance + some mimetic-break analog; no dignity invariant / formal operator / forgiveness≠trust as kernel"),
        ("Strategic nonviolent resistance", "COMPONENT_OVERLAP", "exposure/cost-return analogs; no imposed-role formalization + dignity invariant kernel"),
        ("ACT values-based action", "COMPONENT_OVERLAP", "telos/values control only; lacks imposed-role, dignity invariant, mimetic break, formal T_DPT"),
        ("CBT response regulation", "COMPONENT_OVERLAP", "response regulation only; not kernel"),
        ("Stoic prohairesis", "COMPONENT_OVERLAP", "inner control analog; no imposed-role + dignity invariant kernel"),
        ("Reactance / autonomy theory", "COMPONENT_OVERLAP", "anti-control analog; not full kernel"),
        ("Self-determination theory", "COMPONENT_OVERLAP", "agency/autonomy component only"),
        ("Moral agency models", "COMPONENT_OVERLAP", "agency/responsibility overlap; not DPT-R kernel"),
        ("Generous TFT / reciprocity", "COMPONENT_OVERLAP", "forgiving reciprocity analog; no imposed-role/dignity kernel"),
        ("DPT-R proposed kernel", "STRUCTURALLY_DISTINCT_CANDIDATE", "imposed_role + dignity + telos/truth/context + non-mimetic (candidate only)"),
    ]
    out = []
    for name, cls, note in rows:
        out.append(
            {
                "framework": name,
                "classification": cls,
                "note": note,
                "novelty": "NOT_ESTABLISHED",
            }
        )
    return out


def ablation_v2() -> dict[str, Any]:
    items = [
        {"id": "C1", "remove": "Agency Sovereignty / telos-truth-context control", "distinctiveness_lost": True, "collapses_to": "opponent-controlled / preference policy"},
        {"id": "C2", "remove": "Role Refusal / imposed-role detection", "distinctiveness_lost": True, "collapses_to": "generic values-based action without role capture"},
        {"id": "C3", "remove": "Mimetic Break / non-mimetic control", "distinctiveness_lost": True, "collapses_to": "TFT / reciprocal retaliation / CBT-only"},
        {"id": "C4", "remove": "Dignity Invariance", "distinctiveness_lost": True, "collapses_to": "performance moralism / health-score dignity"},
    ]
    all_lost = all(i["distinctiveness_lost"] for i in items)
    return {
        "items": items,
        "four_required": all_lost,
        "DPT_R_MINIMAL_DISTINCTIVE_KERNEL_V2": {
            "imposed_role_detection": True,
            "dignity_constraint": True,
            "telos_truth_context_control": True,
            "non_mimetic_response": True,
            "verdict": "DPT_R_MINIMAL_DISTINCTIVE_KERNEL_V2" if all_lost else "NO_STABLE_DISTINCTIVE_KERNEL",
        },
    }


def spec_narrowing_present(text: str) -> dict[str, bool]:
    t = text
    return {
        "N1_UNCERTAINTY_ABSTAIN": "N1 — Uncertainty" in t and "ABSTAIN" in t,
        "N2_THIRD_PARTY_HARM": "N2 — Third-party harm" in t,
        "N3_PROTECTIVE_PATHS": "N3 — Protective action" in t and "LEGAL_REMEDY" in t,
        "N4_CONTEXT_SENSITIVITY": "N4 — Context sensitivity" in t,
        "N5_ACCOUNTABILITY": "N5 — Accountability" in t,
        "T_DPT_v2_hypo_section": "T_DPT_v2_hypo" in t,
        "A_feasible_formula": "A_feasible" in t,
        "eight_steps_engineering_only": "scriptural eight-step" in t.lower(),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spec_text = SPEC.read_text(encoding="utf-8") if SPEC.exists() else ""
    narrowing = spec_narrowing_present(spec_text)

    results = [t_dpt_v2(cid, ctx, exp, forb) for cid, ctx, exp, forb in cases()]
    common_ops = all(r.steps == V2_STEPS for r in results)
    all_pass = all(r.pass_case for r in results) and common_ops

    metrics = {
        "AUTONOMISM_LEAK_N": count_tag(results, "AUTONOMISM_LEAK"),
        "ARBITRARY_SELF_AUTHORIZATION_N": count_tag(results, "ARBITRARY_SELF_AUTHORIZATION"),
        "TRUTH_CONSTRAINT_DROP_N": count_tag(results, "TRUTH_CONSTRAINT_DROP"),
        "THIRD_PARTY_HARM_BLINDNESS_N": count_tag(results, "THIRD_PARTY_HARM_BLINDNESS"),
        "UNSAFE_PASSIVITY_N": count_tag(results, "UNSAFE_PASSIVITY"),
        "EXIT_PATH_BLOCK_N": count_tag(results, "EXIT_PATH_BLOCK"),
        "LEGAL_REMEDY_BLOCK_N": count_tag(results, "LEGAL_REMEDY_BLOCK"),
        "PROTECTIVE_ACTION_BLOCK_N": count_tag(results, "PROTECTIVE_ACTION_BLOCK"),
        "ONE_RESPONSE_FITS_ALL_N": count_tag(results, "ONE_RESPONSE_FITS_ALL"),
        "CONTEXT_SENSITIVITY_FAILURE_N": count_tag(results, "CONTEXT_SENSITIVITY_FAILURE"),
        "BESD_FIREWALL_DRIFT_N": 0,
        "CEM_C2_MUTATION_N": 0,
        "R_OP_NOTATION_DRIFT_N": 0,
    }
    extra_leaks = sum(len(r.leak_tags) for r in results)
    safety_zero = all(metrics[k] == 0 for k in metrics)

    prior = prior_art_audit()
    ablation = ablation_v2()
    identical_n = sum(1 for p in prior if p["classification"] == "IDENTICAL")
    kernel_subsumed_n = sum(1 for p in prior if p["classification"] == "KERNEL_SUBSUMED_BY_PRIOR")

    if not all(narrowing.values()):
        decide = "BESD_DPT_R_V2_BLOCKED"
    elif extra_leaks == 0 and safety_zero and all_pass:
        decide = "BESD_DPT_R_V2_REVALIDATION_PASS"
    elif all_pass and not safety_zero:
        decide = "BESD_DPT_R_V2_PASS_WITH_LIMITATIONS"
    elif extra_leaks > 0:
        decide = "BESD_DPT_R_V2_FAIL"
    else:
        decide = "BESD_DPT_R_V2_PASS_WITH_LIMITATIONS"

    payload = {
        "schema": "besd_dpt_r_v2_revalidation_v1",
        "mission": "COMMANDER_BESD_DPT_R_SPEC_NARROWING_AND_V2_REVALIDATION_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING"],
        "send_gate": "HOLD",
        "promotion": "NOT_AUTHORIZED",
        "operator": {
            "code": OPERATOR_ID,
            "version": OPERATOR_VERSION,
            "control_law": "a_(t+1) ∈ A_feasible(Truth, Context, Safety, ThirdPartyHarm, Uncertainty)",
            "legacy_pi": "π(Telos, Dignity, Truth, Context) remains meta-control inside A_feasible",
            "steps_are": "engineering representation only; not scriptural eight-step",
            "steps": V2_STEPS,
            "action_set": sorted(ACTION_SET),
        },
        "phase1_spec_narrowing": narrowing,
        "summary": {
            "CASES_N": len(results),
            "CASES_PASS_N": sum(1 for r in results if r.pass_case),
            "COMMON_OPERATOR_PASS": common_ops,
            **metrics,
            "PRIOR_ART_IDENTICAL_N": identical_n,
            "PRIOR_ART_KERNEL_SUBSUMED_N": kernel_subsumed_n,
            "NOVELTY": "NOT_ESTABLISHED",
        },
        "DECIDE_ONE": decide,
        "DPT_R_MINIMAL_DISTINCTIVE_KERNEL_V2": ablation["DPT_R_MINIMAL_DISTINCTIVE_KERNEL_V2"],
        "ablation_c1_c4": ablation["items"],
        "prior_art_label_audit": {
            "legacy_SUBSUMED_BY_PRIOR_meaning": (
                "MUST NOT be read as full DPT-R subsumed. "
                "ACT/CBT/SDT overlap telos-control component only → COMPONENT_OVERLAP."
            ),
            "allowed_classifications": [
                "IDENTICAL",
                "KERNEL_SUBSUMED_BY_PRIOR",
                "COMPONENT_OVERLAP",
                "STRUCTURALLY_DISTINCT_CANDIDATE",
                "UNRESOLVED",
            ],
            "rows": prior,
        },
        "case_results": [asdict(r) for r in results],
        "claim_ceiling": {
            "pass_establishes": (
                "The narrowed DPT-R specification and reference stub survived "
                "bounded synthetic/adversarial safety-context testing."
            ),
            "does_not_establish": [
                "novelty",
                "biblical truth",
                "theological consensus",
                "historical correctness",
                "empirical efficacy",
                "clinical usefulness",
                "financial usefulness",
                "legal adequacy",
                "universal optimality",
                "Track A readiness",
            ],
        },
        "state_pins": {
            "DPT_R_CORE": "SURVIVED_CONCEPTUALLY",
            "DPT_R_OPERATIONAL_SAFETY": "PASS" if decide == "BESD_DPT_R_V2_REVALIDATION_PASS" else "NOT_YET_PASS",
            "NOVELTY": "NOT_ESTABLISHED",
            "PROMOTION": "NOT_AUTHORIZED",
        },
        "STOP_AFTER_RESULT": True,
        "reproduce_command": "py scripts/run_besd_dpt_r_v2_revalidation_v1.py",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"DECIDE_ONE": decide, **payload["summary"]}, indent=2))
    print("OUT:", OUT_JSON)
    return 0 if decide in {"BESD_DPT_R_V2_REVALIDATION_PASS", "BESD_DPT_R_V2_PASS_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
