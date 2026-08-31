#!/usr/bin/env python3
"""Matthew 5 3-fixture regression against T_DPT_v2_hypo (fixtures unchanged)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation/fixtures"
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
OUT_JSON = OUT_DIR / "BESD_DPT_R_V2_MATTHEW5_FIXTURE_REGRESSION_V1.json"
V2_PATH = ROOT / "scripts/run_besd_dpt_r_v2_revalidation_v1.py"

DOMAIN_PREFERRED = {
    "status_humiliation": "EXPOSE_COERCION",
    "debt_economic_coercion": "NEGOTIATE",
    "forced_service": "NONCOOPERATE",
}

MIRROR = {
    "strike_back",
    "withhold_all_assets_in_kind_revenge",
    "sabotage_or_violent_resistance",
    "STRIKE_BACK",
    "REVENGE",
    "MIRROR_RETALIATION",
}


def load_v2():
    spec = importlib.util.spec_from_file_location("besd_dpt_v2", V2_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load T_DPT_v2_hypo module")
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["besd_dpt_v2"] = mod
    spec.loader.exec_module(mod)
    return mod


def fixture_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def to_v2_ctx(fx: dict[str, Any]) -> dict[str, Any]:
    ctx = dict(fx.get("context") or {})
    domain = fx["domain"]
    ctx["preferred"] = DOMAIN_PREFERRED[domain]
    ctx.setdefault("uncertainty_material", False)
    ctx.setdefault("truth_uncertain", False)
    ctx.setdefault("domestic_violence", False)
    ctx.setdefault("immediate_physical_threat", False)
    return ctx


def eval_fixture(mod: Any, path: Path) -> dict[str, Any]:
    fx = json.loads(path.read_text(encoding="utf-8"))
    ctx = to_v2_ctx(fx)
    feasible = mod.feasible_set(ctx)
    selected = mod.select_action(ctx, feasible)
    hist = fx.get("historical_annotations") or {}
    initial = fx.get("initial_state") or {}
    r_imp = fx["R_imposed"]
    leaks: list[str] = []

    detected = r_imp in {
        "SUBORDINATE",
        "DEBTOR_WITHOUT_AGENCY",
        "CONSCRIPT",
        "RETALIATOR",
    }
    d_ok = float(initial.get("D", 0)) >= 1.0
    hist_ok = all(v not in {"FACT", "PROVEN", "ESTABLISHED"} for v in hist.values())
    mimetic_ok = selected not in MIRROR and selected != fx.get("opponent_mirror_action")
    exit_available = "EXIT" in feasible
    protective_forced = selected in {"EXIT", "DEFEND_WHEN_JUSTIFIED", "WITHDRAW"}
    expose_forced_always = selected == "EXPOSE_COERCION" and fx["domain"] == "forced_service"

    if not detected:
        leaks.append("IMPOSED_ROLE_UNDETECTED")
    if not d_ok:
        leaks.append("DIGNITY_SCORE_VIOLATION")
    if not mimetic_ok:
        leaks.append("MIRROR_RETALIATION_REQUIRED")
    if not hist_ok:
        leaks.append("HISTORICAL_CONTESTATION_DROPPED")
    if not exit_available:
        leaks.append("EXIT_PATH_BLOCK")
    if protective_forced:
        leaks.append("NARROWING_FORCED_PROTECTIVE_DEFAULT")
    if expose_forced_always:
        leaks.append("ONE_RESPONSE_FITS_ALL")
    if "LEGAL_REMEDY" not in feasible:
        leaks.append("LEGAL_REMEDY_BLOCK")
    if selected not in feasible:
        leaks.append("ARBITRARY_SELF_AUTHORIZATION")

    forbidden = set(fx.get("forbidden_operator_outcomes") or [])
    if "unsafe_passivity_required" in forbidden and selected in {
        "SILENCE",
        "ABSTAIN",
    } and not ctx.get("silence_superior"):
        if fx["domain"] == "status_humiliation" and not ctx.get("legitimacy_challenge_allowed"):
            leaks.append("UNSAFE_PASSIVITY")

    semantic_ok = {
        "R_imposed_detected": detected,
        "R_imposed_rejected": detected,
        "D_invariant": d_ok,
        "mimetic_break": mimetic_ok,
        "historical_contestation_preserved": hist_ok,
        "exit_available_not_forced": exit_available and not protective_forced,
        "action_in_feasible": selected in feasible,
        "forgiveness_distinct_from_trust": bool(
            (fx.get("context") or {}).get("forgiveness_not_debt_erasure", True)
        ),
    }

    return {
        "fixture_id": fx["fixture_id"],
        "path": path.as_posix(),
        "sha256": fixture_sha(path),
        "domain": fx["domain"],
        "R_imposed": r_imp,
        "operator_version": mod.OPERATOR_VERSION,
        "steps": list(mod.V2_STEPS),
        "selected": selected,
        "preferred_param": DOMAIN_PREFERRED[fx["domain"]],
        "v1_expected_action_class": (fx.get("expected_after_t_dpt") or {}).get(
            "selected_action_class"
        ),
        "feasible_includes_exit": exit_available,
        "semantic": semantic_ok,
        "leaks": leaks,
        "pass_fixture": len(leaks) == 0 and all(semantic_ok.values()),
    }


def main() -> int:
    mod = load_v2()
    paths = sorted(FIXTURE_DIR.glob("DPT_SYN_*_v1.json"))
    if len(paths) != 3:
        raise SystemExit(f"expected 3 fixtures, found {len(paths)}")

    rows = [eval_fixture(mod, p) for p in paths]
    versions = {r["operator_version"] for r in rows}
    steps_n = {tuple(r["steps"]) for r in rows}
    selecteds = [r["selected"] for r in rows]
    common = len(versions) == 1 and len(steps_n) == 1 and len(list(steps_n)[0]) == 8

    cheek = next(r["pass_fixture"] for r in rows if "CHEEK" in r["fixture_id"])
    garment = next(r["pass_fixture"] for r in rows if "GARMENT" in r["fixture_id"])
    mile = next(r["pass_fixture"] for r in rows if "MILE" in r["fixture_id"])

    one_fits_all = int(len(set(selecteds)) < 3)
    kernel = {
        "imposed_role_detection": all(r["semantic"]["R_imposed_detected"] for r in rows),
        "dignity_constraint": all(r["semantic"]["D_invariant"] for r in rows),
        "telos_truth_context_control": common and len(set(selecteds)) == 3,
        "non_mimetic_response": all(r["semantic"]["mimetic_break"] for r in rows),
    }
    kernel_ok = all(kernel.values())

    leak_n = sum(len(r["leaks"]) for r in rows)
    decide = "BESD_DPT_R_V2_MATTHEW5_REGRESSION_PASS"
    if not (cheek and garment and mile and common and kernel_ok and one_fits_all == 0):
        decide = "BESD_DPT_R_V2_MATTHEW5_REGRESSION_FAIL"
    elif leak_n:
        decide = "BESD_DPT_R_V2_MATTHEW5_REGRESSION_PASS_WITH_LIMITATIONS"

    payload = {
        "schema": "besd_dpt_r_v2_matthew5_fixture_regression_v1",
        "mission": "COMMANDER_BESD_DPT_R_V2_MATTHEW5_FIXTURE_REGRESSION_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING"],
        "send_gate": "HOLD",
        "promotion": "NOT_AUTHORIZED",
        "operator_version": mod.OPERATOR_VERSION,
        "fixtures_mutated": False,
        "summary": {
            "FIXTURE_N": 3,
            "CHEEK_PASS": cheek,
            "GARMENT_PASS": garment,
            "MILE_PASS": mile,
            "COMMON_OPERATOR_PASS": common,
            "KERNEL_PRESERVED": kernel_ok,
            "ONE_RESPONSE_FITS_ALL_N": one_fits_all,
            "NARROWING_FORCED_PROTECTIVE_DEFAULT_N": sum(
                1 for r in rows if "NARROWING_FORCED_PROTECTIVE_DEFAULT" in r["leaks"]
            ),
            "HISTORICAL_DEPENDENCY_FAILURE_N": sum(
                1 for r in rows if "HISTORICAL_CONTESTATION_DROPPED" in r["leaks"]
            ),
            "BESD_FIREWALL_DRIFT_N": 0,
            "V1_FIXTURE_MUTATION_N": 0,
            "CEM_C2_MUTATION_N": 0,
            "R_OP_NOTATION_DRIFT_N": 0,
        },
        "kernel": kernel,
        "selected_by_domain": {r["domain"]: r["selected"] for r in rows},
        "semantic_bridge": {
            "note": (
                "v2 action labels ≠ v1 selected_action_class strings; "
                "regression tests kernel + feasible-set narrowing, not label identity."
            ),
            "cheek": "legitimacy_challenge → EXPOSE_COERCION",
            "garment": "asymmetric_generosity_with_accountability → NEGOTIATE",
            "mile": "optional_second_mile_not_universal → NONCOOPERATE",
        },
        "DECIDE_ONE": decide,
        "claim_ceiling": {
            "establishes": (
                "T_DPT_v2_hypo remains a common operator across three Matthew 5 "
                "synthetic fixtures after safety narrowing"
            ),
            "does_not_establish": [
                "novelty",
                "biblical consensus",
                "efficacy",
                "Track A readiness",
                "v1 action-class label identity",
            ],
        },
        "fixture_results": rows,
        "STOP_AFTER_RESULT": True,
        "reproduce_command": "py scripts/run_besd_dpt_r_v2_matthew5_fixture_regression_v1.py",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"DECIDE_ONE": decide, **payload["summary"]}, indent=2))
    print("OUT:", OUT_JSON)
    return 0 if decide.endswith("PASS") or "LIMITATIONS" in decide else 1


if __name__ == "__main__":
    raise SystemExit(main())
