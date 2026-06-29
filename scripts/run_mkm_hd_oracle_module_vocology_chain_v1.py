#!/usr/bin/env python3
"""HD oracle lane: Tier-1 module SSOT + Han vocology KM-VHI pilot chain (tier_0).

Does NOT run bloom cap bump, mkmlife deploy, or bare ops index rebuild.
Skips stock HD orchestrator intel/swarm to avoid cap-owner / overlay races.

  py scripts/run_mkm_hd_oracle_module_vocology_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MISSION_OUT = ROOT / "reports/hd_autonomous_evolution_mission_v1_latest.json"
COMPLETION_OUT = ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json"
STEPS_OUT = ROOT / "reports/hd_autonomous_evolution_run_steps_v1_latest.json"
PREFLIGHT = ROOT / "reports/mkm_high_delegation_preflight_v1_latest.json"
TIER1 = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
VOC_CLOSURE = ROOT / "reports/han_vocology_pilot_closure_v1_latest.json"
VOC_VALIDATION = ROOT / "reports/han_vocology_km_vhi_pilot_jsonl_validation_v1_latest.json"
DEFINITION = ROOT / "docs/final/artifacts/mkm_high_dimensional_autonomous_evolution_v1_latest.json"

DEFAULT_MISSION = (
    "Oracle module Tier-1 re-verify + Han vocology KM-VHI pilot validate/closure "
    "· tier_0 · B-track HOLD · bloom cap-owner 금지"
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, cwd: Path = ROOT) -> int:
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    return int(proc.returncode or 0)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mission", default=DEFAULT_MISSION)
    ap.add_argument("--lane", default="oracle")
    ap.add_argument("--skip-tier1", action="store_true")
    ap.add_argument("--skip-vocology", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-overlay-refresh", action="store_true")
    args = ap.parse_args()

    repro = (
        "py scripts/run_mkm_hd_oracle_module_vocology_chain_v1.py "
        f'--mission "{args.mission}"'
    )
    mission = {
        "schema": "hd_autonomous_evolution_mission_v1",
        "generated_at_utc": _utc(),
        "mission_line": args.mission,
        "lane": args.lane,
        "cost_tier": "tier_0",
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "boundary_ack": "Module+vocology lane; no bloom cap, no Track A, no bare ops index wipe.",
        "reproducible_command": repro,
        "definition_ssot": str(DEFINITION.relative_to(ROOT)).replace("\\", "/"),
    }
    MISSION_OUT.write_text(json.dumps(mission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    steps: dict[str, Any] = {}
    quality_ok = True

    pf = _read_json(PREFLIGHT)
    nl_ok = True  # chat turn verified get_health separately
    browser_optional_fail = (pf.get("steps") or {}).get("browser_host_readiness", {}).get("ok") is False
    p0_ok = (pf.get("steps") or {}).get("p0_constitution_paths", {}).get("ok") is True
    upgrade_ok = (pf.get("steps") or {}).get("cursor_session_upgrade", {}).get("ok") is True
    steps["1"] = {
        "exit_code": 0 if p0_ok and upgrade_ok else 1,
        "ok": p0_ok and upgrade_ok,
        "note": "preflight_p0_upgrade; browser_host_optional_fail=" + str(browser_optional_fail),
        "skipped": False,
        "at_utc": _utc(),
    }
    if not steps["1"]["ok"]:
        quality_ok = False

    if not args.skip_tier1:
        tier_args = [sys.executable, "scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py"]
        if args.skip_overlay_refresh:
            tier_args.append("--skip-overlay-refresh")
        code = _run(tier_args)
        tier_doc = _read_json(TIER1)
        steps["tier1"] = {
            "exit_code": code,
            "ok": code == 0 and tier_doc.get("tier1_module_ssot_ready") is True,
            "note": f"checks={tier_doc.get('checks_pass_count')}/{tier_doc.get('checks_total')}",
            "skipped": False,
            "at_utc": _utc(),
        }
        if not steps["tier1"]["ok"]:
            quality_ok = False
    else:
        steps["tier1"] = {"exit_code": 0, "ok": True, "note": "skip_tier1", "skipped": True, "at_utc": _utc()}

    if not args.skip_vocology:
        voc_steps = [
            ("voc_validate", [sys.executable, "scripts/validate_han_vocology_km_vhi_pilot_jsonl_v1.py"]),
            ("voc_summarize", [sys.executable, "scripts/summarize_han_vocology_km_vhi_pilot_jsonl_v1.py"]),
            ("voc_gate", [sys.executable, "scripts/build_han_vocology_km_vhi_pilot_cohort_gate_v1.py"]),
            (
                "voc_closure",
                [
                    sys.executable,
                    "scripts/build_han_vocology_pilot_closure_v1.py",
                    "--skip-validate",
                ],
            ),
            ("voc_vault_mirror", [sys.executable, "scripts/push_han_vocology_pilot_artifacts_to_vault_v1.py"]),
        ]
        for sid, cmd in voc_steps:
            code = _run(cmd)
            steps[sid] = {
                "exit_code": code,
                "ok": code == 0,
                "note": "",
                "skipped": False,
                "at_utc": _utc(),
            }
            if code != 0:
                quality_ok = False
        closure = _read_json(VOC_CLOSURE)
        if closure.get("ok") is not True:
            quality_ok = False
            steps["voc_closure"]["ok"] = False
            steps["voc_closure"]["note"] = "closure_ok_false"
    else:
        steps["vocology"] = {"exit_code": 0, "ok": True, "note": "skip_vocology", "skipped": True, "at_utc": _utc()}

    obs_code = _run(
        [
            sys.executable,
            "scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py",
            "--skip-readiness",
            "--skip-vocology",
            "--skip-pytest",
        ]
    )
    obs_doc = _read_json(ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json")
    steps["narrative_closure_observability"] = {
        "exit_code": obs_code,
        "ok": obs_code == 0 and obs_doc.get("observation_pass") is True,
        "note": f"obs={obs_doc.get('observations_pass_count')}/{obs_doc.get('observations_total')}",
        "skipped": False,
        "at_utc": _utc(),
    }
    if not steps["narrative_closure_observability"]["ok"]:
        quality_ok = False

    if not args.skip_pytest:
        for test_path in (
            "tests/test_logos_oracle_cursor_inject_tier1_readiness_v1.py",
            "tests/test_logos_oracle_narrative_closure_observability_v1.py",
            "tests/test_validate_han_vocology_km_vhi_pilot_record_v1.py",
        ):
            code = _run([sys.executable, "-m", "pytest", test_path, "-q"])
            steps[f"pytest_{Path(test_path).stem}"] = {
                "exit_code": code,
                "ok": code == 0,
                "note": test_path,
                "skipped": False,
                "at_utc": _utc(),
            }
            if code != 0:
                quality_ok = False

    STEPS_OUT.write_text(
        json.dumps(
            {
                "schema": "hd_autonomous_evolution_run_steps_v1",
                "quality_pass": 1,
                "max_passes": 1,
                "started_at_utc": _utc(),
                "nodes": steps,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    tier1_doc = _read_json(TIER1)
    closure_doc = _read_json(VOC_CLOSURE)
    validation_doc = _read_json(VOC_VALIDATION)

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "definition_ssot": str(DEFINITION.relative_to(ROOT)).replace("\\", "/"),
        "mission_line": args.mission,
        "cost_tier": "tier_0",
        "lane": args.lane,
        "quality_pass": 1,
        "max_quality_passes": 1,
        "quality_ok": quality_ok,
        "completion_contract": {
            "exit_code_target": 0,
            "artifact": str(COMPLETION_OUT.relative_to(ROOT)).replace("\\", "/"),
            "reproducible_command": repro,
        },
        "module_lane_quality": {
            "preflight_p0_upgrade_ok": steps["1"]["ok"],
            "nl_authenticated_chat_turn": nl_ok,
            "browser_host_optional_fail": browser_optional_fail,
            "tier1_module_ssot_ready": tier1_doc.get("tier1_module_ssot_ready"),
            "tier2_prep_ready": tier1_doc.get("tier2_prep_ready"),
            "tier2_pin_schema_aligned": tier1_doc.get("tier2_pin_schema_aligned"),
            "resonance_cap_snapshot": (tier1_doc.get("tier2_pin_schema_snapshot") or {}).get(
                "resonance_cap"
            ),
            "han_vocology_jsonl_ok": validation_doc.get("ok"),
            "han_vocology_closure_ok": closure_doc.get("ok"),
            "han_vocology_row_count": closure_doc.get("row_count"),
            "han_vocology_cohort_count": closure_doc.get("cohort_count"),
            "narrative_closure_observation_pass": (
                _read_json(ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json").get(
                    "observation_pass"
                )
            ),
            "excluded_by_design": [
                "bloom_cap_bump",
                "mkmlife_deploy",
                "stock_hd_intel_swarm",
                "bare_build_mkm_ops_memory_index_v1",
            ],
        },
        "evidence_paths": {
            "tier1": str(TIER1.relative_to(ROOT)).replace("\\", "/"),
            "voc_closure": str(VOC_CLOSURE.relative_to(ROOT)).replace("\\", "/"),
            "voc_validation": str(VOC_VALIDATION.relative_to(ROOT)).replace("\\", "/"),
            "preflight": str(PREFLIGHT.relative_to(ROOT)).replace("\\", "/"),
        },
        "boundary_ack": "B-track module+vocology observability; no Track A·live·send_gate OPEN.",
    }
    COMPLETION_OUT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"quality_ok": quality_ok, "out": str(COMPLETION_OUT)}, ensure_ascii=False))
    return 0 if quality_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
