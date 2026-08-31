#!/usr/bin/env python3
"""BESD DPT-R stub operator safety-path enumeration (B-track; no Track A).

Closes red-team gap: stub lacked enumerated EXIT/REPORT/LEGAL_REMEDY/PROTECT/ABSTAIN
paths. Additive sidecar block on stub only — no base codebook mutation, no theory
expansion of T_DPT steps, no Biblical Embodied Life book skeleton, R↛G intact.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STUB = (
    ROOT
    / "docs/research/besd/dpt_r_fixture_validation/stub"
    / "MKM_LOGOS_DYNAMICS_CODEBOOK_V0_1_DPT_STUB.json"
)
SAFETY_SIDECAR = (
    ROOT / "docs/research/besd/dpt_r_red_team/DPT_R_MINIMAL_SAFETY_SIDECAR_V1.json"
)
RED_TEAM = (
    ROOT / "docs/research/besd/dpt_r_fixture_validation/BESD_DPT_R_RED_TEAM_V1.json"
)
CONSOL = (
    ROOT
    / "docs/research/besd/besd_v0_2_consolidation"
    / "BESD_V0_2_CONSOLIDATION_RECEIPT_v0.1.json"
)
OUT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
OUT_RECEIPT = OUT_DIR / "BESD_DPT_R_STUB_SAFETY_PATH_ENUMERATION_RECEIPT_V1.json"
OUT_ENUM = OUT_DIR / "BESD_DPT_R_STUB_SAFETY_PATH_ENUMERATION_V1.json"

# Mission-required + red-team axis2 minimum (research_only enumeration).
REQUIRED_PATHS = (
    "EXIT",
    "REPORT",
    "LEGAL_REMEDY",
    "PROTECT",
    "ABSTAIN",
)

# Broader operator-feasible set (aligns with T_DPT_v2 action_set; stub cites, does not run).
ENUMERATED_PATHS = (
    "ABSTAIN",
    "DEFER",
    "SEEK_INFORMATION",
    "SEEK_COUNSEL",
    "WITHDRAW",
    "EXIT",
    "SEEK_HELP",
    "REPORT",
    "PROTECT",
    "PROTECT_SELF",
    "PROTECT_THIRD_PARTY",
    "LEGAL_REMEDY",
    "INSTITUTIONAL_INTERVENTION",
    "DEFEND_WHEN_JUSTIFIED",
    "PHYSICAL_SELF_PROTECTION_WHEN_JUSTIFIED",
    "SILENCE",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def check_firewall(stub: dict[str, Any]) -> dict[str, Any]:
    refs = stub.get("besd_firewall_refs") or {}
    r_to_g = str(refs.get("R_restoration_to_G", "")).upper()
    theo_bio = str(refs.get("theology_to_biology", "")).upper()
    ok = r_to_g == "FORBIDDEN" and theo_bio == "FORBIDDEN"
    return {
        "R_restoration_to_G": r_to_g,
        "theology_to_biology": theo_bio,
        "R_to_G_firewall": ok,
        "FIREWALL_PASS": ok,
    }


def build_enumeration(stub: dict[str, Any], sidecar: dict[str, Any]) -> dict[str, Any]:
    permitted = list(sidecar.get("permitted_actions_where_context_warrants") or [])
    return {
        "schema": "besd_dpt_r_stub_operator_safety_path_enumeration_v1",
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING", "B_TRACK"],
        "send_gate": "HOLD",
        "theory_expansion": False,
        "operator_steps_mutated": False,
        "base_codebook_mutation": False,
        "note": (
            "Additive enumeration only. Does not rewrite T_DPT_v1_hypo steps; "
            "does not claim runtime selection wired; does not establish novelty/efficacy."
        ),
        "required_paths_mission": list(REQUIRED_PATHS),
        "enumerated_paths": list(ENUMERATED_PATHS),
        "safety_sidecar_permitted_actions": permitted,
        "crosswalk_red_team_gap": {
            "missing_operational_rules_closed": [
                "enumerated EXIT/REPORT/LEGAL_REMEDY/PROTECT paths in operator steps",
                "ABSTAIN under truth uncertainty (path named; runtime still stub)",
            ],
            "still_open_impl_runtime": [
                "stub T_DPT_v1_hypo still ignores pi / A_feasible selection",
                "TRUTH_CONSTRAINT_DROP etc. remain until stub runtime uses enumeration",
            ],
        },
        "aliases": {
            "PROTECT": ["PROTECT_SELF", "PROTECT_THIRD_PARTY"],
            "PHYSICAL_SELF_PROTECTION_WHEN_JUSTIFIED": ["DEFEND_WHEN_JUSTIFIED"],
        },
        "hard_rules_inherited_from_sidecar": sidecar.get("hard_rules_text") or [],
        "stub_operator_ref": {
            "code": (stub.get("operator") or {}).get("code"),
            "version": (stub.get("operator") or {}).get("version"),
            "steps_unchanged": (stub.get("operator") or {}).get("steps"),
        },
        "claim_ceiling": {
            "establishes": "stub documents enumerated safety action paths (research_only)",
            "does_not_establish": [
                "novelty",
                "theological validity",
                "empirical efficacy",
                "health/wellness efficacy",
                "Track A promotion",
                "runtime leak metrics all zero",
            ],
        },
    }


def apply_to_stub(stub: dict[str, Any], enumeration: dict[str, Any]) -> dict[str, Any]:
    out = dict(stub)
    out["operator_safety_path_enumeration"] = {
        "required_paths": list(REQUIRED_PATHS),
        "enumerated_paths": list(ENUMERATED_PATHS),
        "source_artifact": rel(OUT_ENUM),
        "safety_sidecar": rel(SAFETY_SIDECAR),
        "operator_steps_mutated": False,
        "runtime_wired": False,
        "note": "Enumeration cite-only; selection remains out-of-band until stub runtime upgrade.",
    }
    # Keep existing safety_sidecar pointer; refresh timestamp marker only inside enum block.
    out["safety_path_enumeration_status"] = "ENUMERATED_DOCUMENTED_RUNTIME_NOT_WIRED"
    return out


def validate(
    stub: dict[str, Any], enumeration: dict[str, Any], firewall: dict[str, Any]
) -> tuple[bool, list[str], dict[str, Any]]:
    fails: list[str] = []
    block = stub.get("operator_safety_path_enumeration") or {}
    paths = set(block.get("enumerated_paths") or [])
    req = set(REQUIRED_PATHS)
    missing = sorted(req - paths)
    if missing:
        fails.append(f"required_paths_missing:{missing}")
    enum_paths = set(enumeration.get("enumerated_paths") or [])
    if req - enum_paths:
        fails.append(f"enumeration_artifact_missing:{sorted(req - enum_paths)}")
    if (stub.get("operator") or {}).get("steps") != enumeration["stub_operator_ref"][
        "steps_unchanged"
    ]:
        fails.append("operator_steps_mutated_unexpectedly")
    if stub.get("base_codebook_mutation") is not False:
        fails.append("base_codebook_mutation_not_false")
    if stub.get("send_gate") != "HOLD":
        fails.append("send_gate_not_HOLD")
    if not firewall.get("FIREWALL_PASS"):
        fails.append("R_to_G_firewall_fail")
    # Alias coverage: PROTECT family present
    if "PROTECT" not in paths:
        fails.append("PROTECT_absent")
    metrics = {
        "REQUIRED_PATHS_N": len(REQUIRED_PATHS),
        "REQUIRED_PRESENT_N": len(req & paths),
        "ENUMERATED_PATHS_N": len(paths),
        "MISSING_REQUIRED": missing,
        "RUNTIME_WIRED": bool(block.get("runtime_wired")),
        "OPERATOR_STEPS_MUTATED": bool(block.get("operator_steps_mutated")),
        "FIREWALL_PASS": bool(firewall.get("FIREWALL_PASS")),
    }
    return (len(fails) == 0), fails, metrics


def main() -> int:
    for p in (STUB, SAFETY_SIDECAR, RED_TEAM):
        if not p.is_file():
            print(f"FAIL missing:{p}", file=sys.stderr)
            return 2

    stub_pre = load_json(STUB)
    sidecar = load_json(SAFETY_SIDECAR)
    red = load_json(RED_TEAM)
    consol = load_json(CONSOL) if CONSOL.is_file() else {}

    stub_sha_pre = sha256(STUB)
    firewall = check_firewall(stub_pre)
    enumeration = build_enumeration(stub_pre, sidecar)
    stub_post = apply_to_stub(stub_pre, enumeration)
    dump_json(STUB, stub_post)
    dump_json(OUT_ENUM, enumeration)

    ok, fails, metrics = validate(stub_post, enumeration, firewall)
    now = datetime.now(timezone.utc).isoformat()

    red_gaps = (red.get("spec_gaps") or {}).get("missing_operational_rules") or []
    decide = (
        "BESD_DPT_R_STUB_SAFETY_PATH_ENUMERATION_PASS"
        if ok
        else "BESD_DPT_R_STUB_SAFETY_PATH_ENUMERATION_FAIL"
    )

    receipt = {
        "schema": "besd_dpt_r_stub_safety_path_enumeration_receipt_v1",
        "mission": "COMMANDER_BESD_DPT_R_STUB_SAFETY_PATH_ENUMERATION_V1",
        "keep_triple_product_axis": 3,
        "generated_at_utc": now,
        "status": "HYPO",
        "tags": ["HYPO", "research_only", "NON_GATING", "B_TRACK"],
        "send_gate": "HOLD",
        "track_a_promotion": "NOT_AUTHORIZED",
        "theological_validation": "NOT_ESTABLISHED",
        "empirical_validation": "NOT_ESTABLISHED",
        "novelty": "NOT_ESTABLISHED",
        "health_efficacy": "NOT_ESTABLISHED",
        "bible_diet_wellness_book": "HOLD",
        "DECIDE_ONE": decide,
        "STOP_AFTER_RESULT": True,
        "inputs": {
            "stub": rel(STUB),
            "stub_sha256_pre": stub_sha_pre,
            "stub_sha256_post": sha256(STUB),
            "safety_sidecar": rel(SAFETY_SIDECAR),
            "red_team_pack": rel(RED_TEAM),
            "red_team_DECIDE_ONE": red.get("DECIDE_ONE"),
            "consolidation_DECIDE_ONE": consol.get("DECIDE_ONE"),
            "consolidation_next_mission_was": consol.get("next_mission"),
        },
        "red_team_gaps_addressed": {
            "missing_operational_rules_cited": red_gaps,
            "enumeration_closed": [
                "EXIT",
                "REPORT",
                "LEGAL_REMEDY",
                "PROTECT",
                "ABSTAIN",
            ],
            "runtime_selection_still_open": True,
        },
        "firewall_verification": firewall,
        "metrics": metrics,
        "validation_fails": fails,
        "artifacts_written": [rel(STUB), rel(OUT_ENUM), rel(OUT_RECEIPT)],
        "claim_ceiling": enumeration["claim_ceiling"],
        "next_mission": (
            "HOLD stub runtime A_feasible wire OR BWH downstream "
            "(enumeration documented; leak metrics not yet zeroed on v1 stub runtime)"
        ),
        "reproduce_command": "py scripts/run_besd_dpt_r_stub_safety_path_enumeration_v1.py",
    }
    dump_json(OUT_RECEIPT, receipt)

    # Light pointer on consolidation receipt (next_mission only; no promotion mutation).
    if consol and CONSOL.is_file():
        consol_out = dict(consol)
        consol_out["stub_safety_path_enumeration"] = {
            "DECIDE_ONE": decide,
            "receipt": rel(OUT_RECEIPT),
            "enumeration": rel(OUT_ENUM),
            "runtime_wired": False,
        }
        consol_out["next_mission"] = receipt["next_mission"]
        dump_json(CONSOL, consol_out)

    print(
        json.dumps(
            {"DECIDE_ONE": decide, "ok": ok, "fails": fails, "metrics": metrics},
            indent=2,
        )
    )
    print(f"receipt={OUT_RECEIPT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
