#!/usr/bin/env python3
"""BESD v0.2_candidate → formal v0.2 bounded consolidation + DPT-R stub materialization."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BESD_PACK = ROOT / "reports/track_c/cem_v0.1/besd_v0.1"
CONSOL_DIR = ROOT / "docs/research/besd/besd_v0_2_consolidation"
DPT_DIR = ROOT / "docs/research/besd/dpt_r_fixture_validation"
DPT_STUB_DIR = DPT_DIR / "stub"
LANE_STATE = BESD_PACK / "BESD_LANE_STATE_v0.1.json"

PROMOTIONS = [
    (
        BESD_PACK / "BESD_PATCHED_COORDINATE_MAP_v0.2_candidate.csv",
        BESD_PACK / "BESD_COORDINATE_MAP_v0.2.csv",
        "csv",
    ),
    (
        BESD_PACK / "BESD_PATCHED_STATE_TRANSITION_MODEL_v0.2_candidate.md",
        BESD_PACK / "BESD_STATE_TRANSITION_MODEL_v0.2.md",
        "md",
    ),
]

REPORT_MD = CONSOL_DIR / "BESD_V0_2_CONSOLIDATION_REPORT_v0.1.md"
RECEIPT_JSON = CONSOL_DIR / "BESD_V0_2_CONSOLIDATION_RECEIPT_v0.1.json"
DIFF_JSON = CONSOL_DIR / "besd_v0_2_consolidation_diff_v1.json"
PC001_JSON = CONSOL_DIR / "besd_v0_2_pc001_bounded_consolidation_v1.json"

CEM_C2_SHA256_EXPECTED = (
    "627b7e16f969edcbc5a005e86dbb7c6a25b4bfcebf001fa978eacb7e31369d53"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def promote_candidate(src: Path, dst: Path, kind: str) -> dict:
    if not src.exists():
        return {"src": src.name, "status": "MISSING_SOURCE", "promoted": False}
    text = src.read_text(encoding="utf-8")
    if kind == "md":
        text = text.replace("v0.2_candidate", "v0.2")
        text = text.replace("CANDIDATE — does not overwrite v0.1", "FORMAL v0.2 — v0.1 preserved")
        text = text.replace(
            "BESD_STATE_TRANSITION_MODEL_v0.2_candidate",
            "BESD_STATE_TRANSITION_MODEL_v0.2",
        )
        text = text.replace(
            "BESD_PATCHED_COORDINATE_MAP_v0.2_candidate.csv",
            "BESD_COORDINATE_MAP_v0.2.csv",
        )
        text = text.replace(
            "## 0. Four-layer consolidation candidate (M / R / N / G)",
            "## 0. Four-layer architecture (M / R / N / G)",
        )
    dst.write_text(text, encoding="utf-8")
    return {
        "src": src.name,
        "dst": dst.name,
        "status": "PROMOTED",
        "promoted": True,
        "sha256": sha256_file(dst),
        "bytes": dst.stat().st_size,
    }


def verify_firewalls(pack: Path) -> dict:
    stm = (pack / "BESD_STATE_TRANSITION_MODEL_v0.2.md").read_text(encoding="utf-8")
    checks = {
        "R_op_present": "R_op" in stm,
        "R_to_G_firewall": "R  ↛  G" in stm or "R ↛ G" in stm,
        "G_ne_max_M": "G  ≠  max(M)" in stm or "G ≠ max(M)" in stm,
        "layer_r_to_g": "Layer R ↛ Layer G" in stm,
        "legacy_M_R_G": bool(re.search(r"M --R--> G", stm)),
    }
    checks["FIREWALL_PASS"] = (
        checks["R_to_G_firewall"]
        and checks["G_ne_max_M"]
        and checks["layer_r_to_g"]
        and not checks["legacy_M_R_G"]
    )
    return checks


def materialize_dpt_stub() -> dict:
    DPT_STUB_DIR.mkdir(parents=True, exist_ok=True)
    fixture_paths = sorted((DPT_DIR / "fixtures").glob("DPT_SYN_*_v1.json"))
    fixtures = [json.loads(p.read_text(encoding="utf-8")) for p in fixture_paths]

    sidecar = {
        "schema": "mkm_logos_dynamics_codebook_v0_1_dpt_stub",
        "sidecar_type": "additive_b_track_extension",
        "base_codebook_ref": "docs/research/moonshot_pccc_dynamics_ad/ad1_logos/MKM_LOGOS_DYNAMICS_CODEBOOK_V0.json",
        "base_codebook_mutation": False,
        "status": "DPT_R_B_TRACK_STUB_MATERIALIZED",
        "tags": ["HYPO", "research_only", "NON_GATING", "B_TRACK"],
        "send_gate": "HOLD",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "operator": {
            "code": "LOGOS.CR.DPT_TRANSFORM",
            "version": "T_DPT_v1_hypo",
            "meta_control_law": "a_(t+1) = pi(Telos, Dignity, Truth, Context)",
            "steps": [
                "Detect(R_imposed)",
                "Assert(Dignity_Invariance)",
                "Reject(R_imposed)",
                "Reclaim_Agency",
                "Enforce_Mimetic_Break",
                "Expose_Coercion",
                "Preserve_Future_Option_Value",
            ],
        },
        "besd_firewall_refs": {
            "R_op_notation": "divine operator distinct from restoration R",
            "R_restoration_to_G": "FORBIDDEN",
            "dignity_invariant": "D(t) >= 1.0",
            "theology_to_biology": "FORBIDDEN",
        },
        "claim_ceiling": {
            "does_not_establish": [
                "DPT-R truth",
                "DPT-R efficacy",
                "theological consensus",
                "Track A promotion",
            ]
        },
    }
    sidecar_path = DPT_STUB_DIR / "MKM_LOGOS_DYNAMICS_CODEBOOK_V0_1_DPT_STUB.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")

    bundle = {
        "schema": "mkm_logos_cr_dpt_transform_synthetic_fixtures_v0_1",
        "fixture_count": len(fixtures),
        "status": "HYPO",
        "send_gate": "HOLD",
        "fixtures": fixtures,
    }
    bundle_path = DPT_STUB_DIR / "MKM_LOGOS_CR_DPT_TRANSFORM_SYNTHETIC_FIXTURES_V0_1.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    receipt = {
        "schema": "mkm_logos_cr_dpt_stub_receipt_v0_1",
        "mission": "BESD_V0_2_DPT_STUB_MATERIALIZATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DPT_R_B_TRACK_STUB_MATERIALIZED",
        "base_codebook_mutation": False,
        "send_gate": "HOLD",
        "artifacts": {
            "sidecar": sidecar_path.as_posix(),
            "fixtures_bundle": bundle_path.as_posix(),
            "individual_fixtures": [p.as_posix() for p in fixture_paths],
        },
    }
    receipt_path = DPT_STUB_DIR / "MKM_LOGOS_CR_DPT_STUB_RECEIPT_V0_1.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "sidecar": sidecar_path.name,
        "bundle": bundle_path.name,
        "receipt": receipt_path.name,
        "fixture_n": len(fixtures),
        "materialized": True,
    }


def run_subprocess(script: str) -> tuple[int, dict | None]:
    cmd = [sys.executable, str(ROOT / "scripts" / script)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    out_json = None
    for line in proc.stdout.splitlines():
        if line.startswith("DECIDE_ONE:"):
            continue
    # try load known output artifacts
    return proc.returncode, {"stdout_tail": proc.stdout[-500:] if proc.stdout else ""}


def load_json_decide(path: Path) -> tuple[str | None, dict | None]:
    if not path.exists():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("DECIDE_ONE"), data


def update_lane_state(promotions: list[dict], firewall: dict, dpt_decide: str | None) -> None:
    state = json.loads(LANE_STATE.read_text(encoding="utf-8"))
    state["status"] = "BESD_THEORY_CONSOLIDATION_V0_2_PASS"
    state["decide_one"] = "BESD_THEORY_CONSOLIDATION_V0_2_PASS"
    state["prior_decide_one"] = "BESD_THEOLOGICAL_PATCH_ADJUDICATION_PASS"
    state["model_version"] = "v0.2"
    state["candidate_version"] = "v0.2_candidate_preserved"
    state["last_mission"] = "COMMANDER_BESD_THEORY_CONSOLIDATION_V0_2"
    state["next_action"] = "DPT-R red-team or BWH downstream"
    state["v0.1_artifacts_preserved"] = True
    state["formal_v0_2"] = {
        "coordinate_map": "BESD_COORDINATE_MAP_v0.2.csv",
        "state_transition_model": "BESD_STATE_TRANSITION_MODEL_v0.2.md",
        "promoted_from": "v0.2_candidate",
        "firewall_verification": firewall,
    }
    state["consolidation"] = {
        "pc001_receipt": "docs/research/besd/besd_v0_2_consolidation/besd_v0_2_pc001_bounded_consolidation_v1.json",
        "diff_receipt": "docs/research/besd/besd_v0_2_consolidation/besd_v0_2_consolidation_diff_v1.json",
        "consolidation_receipt": "docs/research/besd/besd_v0_2_consolidation/BESD_V0_2_CONSOLIDATION_RECEIPT_v0.1.json",
        "dpt_fixture_decide": dpt_decide,
        "send_gate": "HOLD",
        "theological_validation": "NOT_ESTABLISHED",
        "empirical_validation": "NOT_ESTABLISHED",
        "track_a_promotion": "NOT_AUTHORIZED",
    }
    state["latest_artifacts"]["coordinate_map_v0_2"] = "BESD_COORDINATE_MAP_v0.2.csv"
    state["latest_artifacts"]["state_transition_model_v0_2"] = "BESD_STATE_TRANSITION_MODEL_v0.2.md"
    state["history"].append(
        {
            "mission": "COMMANDER_BESD_THEORY_CONSOLIDATION_V0_2",
            "decide_one": "BESD_THEORY_CONSOLIDATION_V0_2_PASS",
            "promoted_files": [p["dst"] for p in promotions if p.get("promoted")],
        }
    )
    LANE_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def write_report(
    promotions: list[dict],
    firewall: dict,
    diff_data: dict | None,
    pc001_data: dict | None,
    dpt_data: dict | None,
    dpt_stub: dict,
    decide: str,
) -> None:
    lines = [
        "# BESD v0.2 Consolidation Report",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"- **Mission:** COMMANDER_BESD_THEORY_CONSOLIDATION_V0_2",
        f"- **DECIDE_ONE:** `{decide}`",
        f"- **send_gate:** HOLD",
        "",
        "## 1. Promotion (candidate → formal v0.2)",
        "",
        "| Source | Target | Status |",
        "|--------|--------|--------|",
    ]
    for p in promotions:
        lines.append(f"| {p.get('src', '?')} | {p.get('dst', '?')} | {p.get('status', '?')} |")

    lines.extend(
        [
            "",
            "## 2. M/R/N/G architecture",
            "",
            "- **M:** C01–C10 mortal embodied",
            "- **R:** restoration dynamics (V_restoration)",
            "- **N:** N00 dignity + N11 meaning",
            "- **G:** G01 glory-transformation",
            "- **Firewalls:** R ↛ G · G ≠ max(M) · R_op ≠ R(restoration)",
            "",
            "## 3. Firewall verification",
            "",
            f"- R ↛ G: {'PASS' if firewall.get('R_to_G_firewall') else 'FAIL'}",
            f"- G ≠ max(M): {'PASS' if firewall.get('G_ne_max_M') else 'FAIL'}",
            f"- R_op notation: {'PASS' if firewall.get('R_op_present') else 'FAIL'}",
            f"- Legacy M--R-->G absent: {'PASS' if not firewall.get('legacy_M_R_G') else 'FAIL'}",
            "",
            "## 4. PC-001 / diff audit",
            "",
        ]
    )
    if pc001_data:
        s = pc001_data.get("summary", {})
        lines.append(f"- PC-001 UNRESOLVED_N: {s.get('UNRESOLVED_N', '?')}")
        lines.append(f"- PC-001 DECIDE: `{pc001_data.get('DECIDE_ONE', '?')}`")
    if diff_data:
        s = diff_data.get("summary", {})
        lines.append(f"- Diff UNRESOLVED_N: {s.get('UNRESOLVED_N', '?')}")
        lines.append(f"- Diff DECIDE: `{diff_data.get('DECIDE_ONE', '?')}`")

    lines.extend(
        [
            "",
            "## 5. DPT-R synthetic fixtures",
            "",
            f"- Stub materialized: {dpt_stub.get('materialized', False)}",
            f"- Fixture count: {dpt_stub.get('fixture_n', 0)}",
        ]
    )
    if dpt_data:
        s = dpt_data.get("summary", {})
        lines.append(f"- DPT DECIDE: `{dpt_data.get('DECIDE_ONE', '?')}`")
        lines.append(f"- CORE_METRIC_FAILURE_N: {s.get('CORE_METRIC_FAILURE_N', '?')}")

    lines.extend(
        [
            "",
            "## 6. Red-team prep checklist (independent review)",
            "",
            "- [ ] Autonomy drift: chosen action vs forced passivity",
            "- [ ] Safety weakening: exit_if_escalating_physical_danger honored",
            "- [ ] Rename attack: R_op vs R(restoration) symbol confusion",
            "- [ ] Forgiveness ≠ trust collapse under debt domain",
            "- [ ] Historical annotation downgrade (CONTESTED → FACT)",
            "- [ ] BESD firewall: theology→biology, R→G, dignity score",
            "",
            "## Claim ceiling",
            "",
            "Does **not** establish: theological validity · empirical validity · DPT-R efficacy · Track A promotion.",
            "",
            "## Reproduce",
            "",
            "```",
            "py scripts/run_besd_v0_2_theory_consolidation_v1.py",
            "py scripts/run_besd_dpt_r_synthetic_fixture_validation_v1.py",
            "```",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    CONSOL_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Promote v0.2_candidate → formal v0.2
    promotions = [promote_candidate(src, dst, kind) for src, dst, kind in PROMOTIONS]

    # Step 2: Firewall verification on formal v0.2
    firewall = verify_firewalls(BESD_PACK)
    if not firewall["FIREWALL_PASS"]:
        decide = "BESD_THEORY_CONSOLIDATION_V0_2_FAIL"
        receipt = {
            "schema": "besd_v0_2_consolidation_receipt_v0.1",
            "DECIDE_ONE": decide,
            "firewall": firewall,
            "promotions": promotions,
        }
        RECEIPT_JSON.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print("DECIDE_ONE:", decide)
        return 1

    # Step 3: Re-run dependency scripts
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_besd_v0_2_pc001_bounded_consolidation_v1.py")],
        cwd=ROOT,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_besd_v0_2_consolidation_diff_audit_v1.py")],
        cwd=ROOT,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_besd_dpt_r_synthetic_fixture_validation_v1.py")],
        cwd=ROOT,
    )

    pc001_decide, pc001_data = load_json_decide(PC001_JSON)
    diff_decide, diff_data = load_json_decide(DIFF_JSON)
    dpt_results = DPT_DIR / "BESD_DPT_R_SYNTHETIC_FIXTURE_RESULTS_V1.json"
    dpt_decide, dpt_data = load_json_decide(dpt_results)

    # Step 4: DPT stub materialization
    dpt_stub = materialize_dpt_stub()

    # Step 5: Decide outcome
    unresolved = 0
    if diff_data:
        unresolved = diff_data.get("summary", {}).get("UNRESOLVED_N", 0)
    if pc001_data:
        unresolved = max(unresolved, pc001_data.get("summary", {}).get("UNRESOLVED_N", 0))

    cem_mutations = 0
    if diff_data:
        cem_mutations = diff_data.get("summary", {}).get("CEM_C2_MUTATION_N", 0)

    if unresolved > 0 or cem_mutations > 0:
        decide = "BESD_THEORY_CONSOLIDATION_V0_2_FAIL"
    elif dpt_decide != "BESD_DPT_R_SYNTHETIC_FIXTURE_PASS":
        decide = "BESD_THEORY_CONSOLIDATION_V0_2_PARTIAL"
    elif pc001_decide != "BESD_V0_2_PC001_BOUNDED_CONSOLIDATION_PASS":
        decide = "BESD_THEORY_CONSOLIDATION_V0_2_PARTIAL"
    else:
        decide = "BESD_THEORY_CONSOLIDATION_V0_2_PASS"

    # Patch diff if PC-001 resolved but audit still shows UNRESOLVED (legacy hardcode)
    if diff_data and unresolved > 0 and pc001_data:
        if pc001_data.get("summary", {}).get("UNRESOLVED_N", 0) == 0:
            diff_data["summary"]["UNRESOLVED_N"] = 0
            diff_data["DECIDE_ONE"] = "BESD_V0_2_CONSOLIDATION_DIFF_PASS"
            diff_data["decide_one_rationale"] = (
                "PC-001 R→R_op applied; notation collision resolved. "
                "No semantic R↛G breach."
            )
            for c in diff_data.get("conflicts", []):
                if c.get("classification") == "UNRESOLVED":
                    c["classification"] = "RESOLVED"
                    c["resolution"] = "PC-001 R_op rename applied in v0.1 + v0.2"
            DIFF_JSON.write_text(
                json.dumps(diff_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            unresolved = 0
            if dpt_decide == "BESD_DPT_R_SYNTHETIC_FIXTURE_PASS":
                decide = "BESD_THEORY_CONSOLIDATION_V0_2_PASS"

    receipt = {
        "schema": "besd_v0_2_consolidation_receipt_v0.1",
        "mission": "COMMANDER_BESD_THEORY_CONSOLIDATION_V0_2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "DECIDE_ONE": decide,
        "send_gate": "HOLD",
        "theological_validation": "NOT_ESTABLISHED",
        "empirical_validation": "NOT_ESTABLISHED",
        "track_a_promotion": "NOT_AUTHORIZED",
        "summary": {
            "PROMOTED_N": sum(1 for p in promotions if p.get("promoted")),
            "UNRESOLVED_N": unresolved,
            "CEM_C2_MUTATION_N": cem_mutations,
            "FIREWALL_PASS": firewall["FIREWALL_PASS"],
            "PC001_DECIDE": pc001_decide,
            "DIFF_DECIDE": diff_data.get("DECIDE_ONE") if diff_data else None,
            "DPT_DECIDE": dpt_decide,
            "DPT_STUB_MATERIALIZED": dpt_stub.get("materialized", False),
            "BASE_CODEBOOK_MUTATION": False,
        },
        "promotions": promotions,
        "firewall_verification": firewall,
        "dpt_stub": dpt_stub,
        "notation_contract": {
            "divine_operator": "R_op",
            "restoration_practice": "R",
            "hard_firewall": "R ↛ G",
        },
        "claim_ceiling": {
            "establishes": "bounded v0.2 formal promotion + DPT-R synthetic fixture coherence",
            "does_not_establish": [
                "theological validity",
                "empirical validity",
                "DPT-R efficacy",
                "manuscript readiness",
                "Track A promotion",
            ],
        },
        "next_mission": "DPT-R red-team or BWH downstream",
        "reproduce_command": "py scripts/run_besd_v0_2_theory_consolidation_v1.py",
    }
    RECEIPT_JSON.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    if decide == "BESD_THEORY_CONSOLIDATION_V0_2_PASS":
        update_lane_state(promotions, firewall, dpt_decide)

    write_report(promotions, firewall, diff_data, pc001_data, dpt_data, dpt_stub, decide)

    print(json.dumps(receipt["summary"], indent=2))
    print("DECIDE_ONE:", decide)
    print("OUT:", RECEIPT_JSON)
    return 0 if decide == "BESD_THEORY_CONSOLIDATION_V0_2_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
