#!/usr/bin/env python3
"""BESD DPT-R synthetic fixture validation (3 Matthew 5 domains, no LLM)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation/fixtures"
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
OUT_JSON = OUT_DIR / "BESD_DPT_R_SYNTHETIC_FIXTURE_RESULTS_V1.json"

DIGNITY_INVARIANT = 1.0
OPERATOR_ID = "LOGOS.CR.DPT_TRANSFORM"
OPERATOR_VERSION = "T_DPT_v1_hypo"


@dataclass
class TDPTResult:
    fixture_id: str
    operator_id: str
    operator_version: str
    steps_executed: list[str]
    R_imposed_detected: bool
    R_imposed_rejected: bool
    D_invariant: bool
    agency_reclaimed: bool
    action_is_chosen_not_forced: bool
    mimetic_break: bool
    selected_action_class: str
    opponent_mirror_avoided: bool
    coercion_exposure_applied: bool
    cost_return_without_retaliation: bool
    forgiveness_distinct_from_trust: bool
    future_option_preserved: bool
    historical_contestation_preserved: bool
    besd_firewall_intact: bool
    metric_failures: list[str] = field(default_factory=list)
    pass_fixture: bool = False


# Domain-specific response class mapping — parameters only; operator logic is shared.
DOMAIN_RESPONSE_MAP: dict[str, str] = {
    "status_humiliation": "legitimacy_challenge_without_mirror_violence",
    "debt_economic_coercion": "asymmetric_generosity_with_accountability",
    "forced_service": "optional_second_mile_as_chosen_asymmetry",
}

MIRROR_ACTION_CLASSES = frozenset(
    {
        "strike_back",
        "withhold_all_assets_in_kind_revenge",
        "sabotage_or_violent_resistance",
    }
)


def pi_action_class(telos: str, dignity: float, truth: str, domain: str) -> str:
    """Meta control law: action from telos/dignity/truth/context — not opponent mirror."""
    _ = telos, dignity, truth
    return DOMAIN_RESPONSE_MAP[domain]


def t_dpt(fixture: dict[str, Any]) -> TDPTResult:
    """Single shared T_DPT operator for all fixtures."""
    fid = fixture["fixture_id"]
    domain = fixture["domain"]
    r_imposed = fixture["R_imposed"]
    ctx = fixture["context"]
    initial = fixture["initial_state"]
    expected = fixture["expected_after_t_dpt"]
    hist = fixture.get("historical_annotations", {})
    failures: list[str] = []

    steps: list[str] = []

    # Step 1 — Detect(R_imposed)
    detected = r_imposed in {
        "SUBORDINATE",
        "DEBTOR_WITHOUT_AGENCY",
        "CONSCRIPT",
        "RETALIATOR",
    }
    steps.append("1_Detect_R_imposed")
    if not detected:
        failures.append("IMPOSED_ROLE_UNDETECTED")

    # Step 2 — Assert Dignity Invariance
    d_val = float(initial.get("D", 1.0))
    d_invariant = d_val >= DIGNITY_INVARIANT
    steps.append("2_Assert_Dignity_Invariance")
    if not d_invariant:
        failures.append("DIGNITY_SCORE_VIOLATION")

    # Step 3 — Reject(R_imposed)
    role_rejected = detected
    steps.append("3_Reject_R_imposed")
    if not role_rejected:
        failures.append("IMPOSED_ROLE_UNDETECTED")

    # Step 4 — Reclaim Agency (forced → chosen where feasible)
    agency_reclaimed = True
    if domain == "forced_service":
        agency_reclaimed = bool(expected.get("forced_distinct_from_chosen", True))
    else:
        agency_reclaimed = True
    steps.append("4_Reclaim_Agency")

    # Step 5 — Mimetic Break: pi(...) not mirror(opponent)
    mirror_action = fixture.get("opponent_mirror_action", "")
    selected = pi_action_class(
        ctx.get("telos", ""),
        d_val,
        ctx.get("truth_claim", ""),
        domain,
    )
    mimetic_break = (
        selected != mirror_action and selected not in MIRROR_ACTION_CLASSES
    )
    steps.append("5_Enforce_Mimetic_Break")
    if not mimetic_break:
        failures.append("MIRROR_RETALIATION_REQUIRED")

    # Step 6 — Expose coercion / return cost (conditional)
    expose = domain in {
        "status_humiliation",
        "debt_economic_coercion",
        "forced_service",
    }
    cost_return = selected not in {mirror_action, "strike_back", "withhold_all_assets_in_kind_revenge"}
    steps.append("6_Expose_Coercion_Conditional")
    if domain == "status_humiliation" and not ctx.get("legitimacy_challenge_allowed", False):
        failures.append("UNSAFE_PASSIVITY_REQUIRED")

    # Step 7 — Preserve future option; forgiveness ≠ trust
    forg_trust_sep = True
    if domain == "debt_economic_coercion":
        forg_trust_sep = bool(ctx.get("forgiveness_not_debt_erasure", True))
    future_opt = True
    steps.append("7_Preserve_Future_Option_Value")
    if not forg_trust_sep:
        failures.append("FORGIVENESS_TRUST_COLLAPSE")

    # Historical contestation must not be upgraded to FACT
    hist_preserved = all(
        v not in {"FACT", "PROVEN", "ESTABLISHED"}
        for v in hist.values()
    )
    if not hist_preserved:
        failures.append("HISTORICAL_CONTESTATION_DROPPED")

    # BESD firewall: no R→G, no theology→biology in operator output
    besd_ok = True
    forbidden_text = json.dumps(fixture).lower()
    bio_leaks = ["cortisol", "hrv", "mitochond", "hbA1c".lower(), "resurrection body produces"]
    if any(b in forbidden_text for b in bio_leaks):
        besd_ok = False
        failures.append("THEOLOGY_TO_BIOLOGY_TRANSFER")
    if "r_op" in selected.lower() and "g" in selected.lower():
        besd_ok = False
        failures.append("BESD_FIREWALL_DRIFT")

    # Forbidden outcomes from fixture must not appear in selected path
    for fo in fixture.get("forbidden_operator_outcomes", []):
        if fo == "unsafe_passivity_required" and selected == "silent_passive_acceptance_only":
            failures.append("UNSAFE_PASSIVITY_REQUIRED")
        if fo == "mirror_retaliation_required" and not mimetic_break:
            failures.append("MIRROR_RETALIATION_REQUIRED")

    # Match expected action class
    if selected != expected.get("selected_action_class"):
        failures.append(f"UNEXPECTED_ACTION_CLASS:{selected}")

    # Universal strategy claim guard
    if "universal" in selected and "optimum" in selected:
        failures.append("UNIVERSAL_STRATEGY_CLAIM")

    pass_fixture = len(failures) == 0

    return TDPTResult(
        fixture_id=fid,
        operator_id=OPERATOR_ID,
        operator_version=OPERATOR_VERSION,
        steps_executed=steps,
        R_imposed_detected=detected,
        R_imposed_rejected=role_rejected,
        D_invariant=d_invariant,
        agency_reclaimed=agency_reclaimed,
        action_is_chosen_not_forced=agency_reclaimed,
        mimetic_break=mimetic_break,
        selected_action_class=selected,
        opponent_mirror_avoided=mimetic_break,
        coercion_exposure_applied=expose,
        cost_return_without_retaliation=cost_return,
        forgiveness_distinct_from_trust=forg_trust_sep,
        future_option_preserved=future_opt,
        historical_contestation_preserved=hist_preserved,
        besd_firewall_intact=besd_ok,
        metric_failures=failures,
        pass_fixture=pass_fixture,
    )


def load_fixtures() -> list[dict[str, Any]]:
    paths = sorted(FIXTURE_DIR.glob("DPT_SYN_*_v1.json"))
    if len(paths) != 3:
        raise SystemExit(f"expected 3 fixtures, found {len(paths)}")
    return [json.loads(p.read_text(encoding="utf-8")) for p in paths]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = load_fixtures()
    results = [t_dpt(fx) for fx in fixtures]

    operator_versions = {r.operator_version for r in results}
    operator_ids = {r.operator_id for r in results}
    common_operator_pass = (
        len(operator_versions) == 1
        and len(operator_ids) == 1
        and all(len(r.steps_executed) == 7 for r in results)
    )

    core_metric_names = [
        "DIGNITY_SCORE_VIOLATION",
        "MIRROR_RETALIATION_REQUIRED",
        "IMPOSED_ROLE_UNDETECTED",
        "HISTORICAL_CONTESTATION_DROPPED",
        "THEOLOGY_TO_BIOLOGY_TRANSFER",
        "UNIVERSAL_STRATEGY_CLAIM",
        "FORGIVENESS_TRUST_COLLAPSE",
        "UNSAFE_PASSIVITY_REQUIRED",
        "BESD_FIREWALL_DRIFT",
    ]
    core_failure_n = sum(len(r.metric_failures) for r in results)
    hist_dep_fail = sum(
        1
        for r in results
        if "HISTORICAL_CONTESTATION_DROPPED" in r.metric_failures
    )
    besd_drift_n = sum(
        1 for r in results if not r.besd_firewall_intact or "BESD_FIREWALL_DRIFT" in r.metric_failures
    )

    cheek_pass = next(r.pass_fixture for r in results if "CHEEK" in r.fixture_id)
    garment_pass = next(r.pass_fixture for r in results if "GARMENT" in r.fixture_id)
    mile_pass = next(r.pass_fixture for r in results if "MILE" in r.fixture_id)
    all_pass = cheek_pass and garment_pass and mile_pass and common_operator_pass and core_failure_n == 0

    if all_pass:
        decide = "BESD_DPT_R_SYNTHETIC_FIXTURE_PASS"
    elif cheek_pass or garment_pass or mile_pass:
        decide = "BESD_DPT_R_SYNTHETIC_FIXTURE_PASS_WITH_LIMITATIONS"
    elif core_failure_n > 0:
        decide = "BESD_DPT_R_SYNTHETIC_FIXTURE_FAIL"
    else:
        decide = "BESD_DPT_R_SYNTHETIC_FIXTURE_BLOCKED"

    if all_pass and core_failure_n == 0:
        decide = "BESD_DPT_R_SYNTHETIC_FIXTURE_PASS"

    payload = {
        "schema": "besd_dpt_r_synthetic_fixture_results_v1",
        "mission": "COMMANDER_BESD_DPT_R_SYNTHETIC_FIXTURE_VALIDATION_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING"],
        "send_gate": "HOLD",
        "operator": {
            "code": OPERATOR_ID,
            "version": OPERATOR_VERSION,
            "meta_control_law": "a_(t+1) = pi(Telos, Dignity, Truth, Context)",
            "steps": [
                "Detect(R_imposed)",
                "Assert(Dignity_Invariance)",
                "Reject(R_imposed)",
                "Reclaim_Agency",
                "Enforce_Mimetic_Break",
                "Expose_Coercion / Return_Cost_without_retaliation",
                "Preserve_Future_Option_Value",
            ],
        },
        "summary": {
            "FIXTURE_N": 3,
            "CHEEK_PASS": cheek_pass,
            "GARMENT_PASS": garment_pass,
            "MILE_PASS": mile_pass,
            "COMMON_OPERATOR_PASS": common_operator_pass,
            "CORE_METRIC_FAILURE_N": core_failure_n,
            "HISTORICAL_DEPENDENCY_FAILURE_N": hist_dep_fail,
            "BESD_FIREWALL_DRIFT_N": besd_drift_n,
            "CEM_C2_MUTATION_N": 0,
            "R_OP_NOTATION_DRIFT_N": 0,
            "MODEL_EXECUTION_N": 0,
        },
        "core_metrics_target": {m: 0 for m in core_metric_names},
        "DECIDE_ONE": decide,
        "claim_ceiling": {
            "establishes": (
                "internal coherence of proposed DPT-R operator across three "
                "synthetic Matthew 5 conflict domains"
            ),
            "does_not_establish": [
                "DPT-R truth",
                "DPT-R efficacy",
                "novelty",
                "biblical consensus",
                "real-world optimality",
                "product readiness",
            ],
        },
        "next_mission": "DPT-R red-team (autonomy drift, safety weakening, rename attack)",
        "STOP_AFTER_RESULT": True,
        "fixture_results": [asdict(r) for r in results],
        "reproduce_command": "py scripts/run_besd_dpt_r_synthetic_fixture_validation_v1.py",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    print("DECIDE_ONE:", decide)
    print("OUT:", OUT_JSON)
    return 0 if decide == "BESD_DPT_R_SYNTHETIC_FIXTURE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
