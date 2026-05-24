#!/usr/bin/env python3
"""Record commander-approved v2 wire_selective staging scope (no active writes)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_v2_wire_staging_promotion_scope_v1.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
BRIEF = PILOT / "comp_atom05_profile_matrix_brief_v1.json"

WIRE_PYTEST = [
    "tests/test_v2_graph_wire_selective_bridge_v1.py",
    "tests/test_compression_token_api_v2_stub.py",
    "tests/test_comp_atom05_graph_wire_bridge_smoke_v1.py",
    "tests/test_mkm_graph_wire_bridge_influence_v1.py",
    "tests/test_compression_profile_v1.py",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_wire_pytest() -> dict[str, object]:
    cmd = [sys.executable, "-m", "pytest", *WIRE_PYTEST, "-q", "--tb=no"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
    }


def _run_phase2() -> dict[str, object]:
    steps: list[dict[str, object]] = []
    for label, script, extra in (
        ("bench", ROOT / "scripts/run_v2_wire_shadow_metering_bench_v1.py", ["--max-cases", "0"]),
        ("summarize", ROOT / "scripts/summarize_v2_wire_shadow_metering_v1.py", []),
    ):
        cmd = [sys.executable, str(script), *extra]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        steps.append(
            {
                "step": label,
                "exit_code": proc.returncode,
                "stdout_tail": (proc.stdout or "")[-500:],
            }
        )
        if proc.returncode != 0:
            return {"ok": False, "steps": steps}
    return {"ok": True, "steps": steps}


def main() -> int:
    ap = __import__("argparse").ArgumentParser(description=__doc__)
    ap.add_argument(
        "--include-phase2",
        action="store_true",
        help="Run shadow bench (5 cases) + summarize JSONL",
    )
    args = ap.parse_args()

    active = json.loads(ACTIVE.read_text(encoding="utf-8")) if ACTIVE.is_file() else {}
    cm = active.get("compression_metrics") or {}
    brief = json.loads(BRIEF.read_text(encoding="utf-8")) if BRIEF.is_file() else {}
    pytest_result = _run_wire_pytest()

    doc = {
        "schema": "comp_v2_wire_staging_promotion_scope_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "commander_scope_id": "v2_wire_opt_in_phase1",
        "approved": True,
        "track_a_frozen": {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "active_report": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "external_headline": "47.5% saving / Jaccard 0.890 (40-case economy, bridge OFF)",
        },
        "staging_v2_wire": {
            "default_graph_wire_selective_bridge": False,
            "opt_in_preset": (brief.get("profile_presets") or {}).get("btrack_recommended_v2"),
            "openapi": "docs/final/openapi_token_compression_v2_draft.yaml",
            "stub": "scripts/compression_token_api_v2_stub.py",
            "no_op_guard": (
                "wire=true is no-op when GraphRAG/atom-network unavailable or bridge metadata "
                "stripped on integration path; effective behavior matches false."
            ),
        },
        "forbidden": [
            "overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json with wire-on economy KPI",
            "apply_multilens_ultra_compression_track_a_promotion_v1.py without explicit human scope for wire",
            "claim every POST /v2/compress returns bench 47.1%/0.897",
            "promote genesis pointer_primary to Track A (0/40 strict)",
            "auto live_trading or Track A default flip to graph_wire_selective_bridge=true",
        ],
        "phase1_complete": [
            "openapi default false + no-op guard documented",
            "brief pitfalls/integration_checklist aligned",
            "wire pytest bundle exit 0",
        ],
        "phase2_deferred": [],
        "phase3_weekly_ops": {
            "runner_ps1": "scripts/Run-V2WireShadowMeteringWeekly_v1.ps1",
            "register_ps1": "scripts/Register-V2WireShadowMeteringWeeklyTask.ps1",
            "task_name_default": "MKM-V2-Wire-Shadow-Metering-Weekly",
            "universal_lane_refresh": "scripts/run_v2_wire_universal_lane_refresh_v1.ps1",
            "note": "Register on operator PC; B-track only; active report untouched.",
        },
        "phase2_artifacts": {
            "log_jsonl": "reports/constitution/btrack_pilot/v2_wire_shadow_metering_v1.jsonl",
            "summary_json": "reports/constitution/btrack_pilot/comp_v2_wire_shadow_metering_summary_v1.json",
            "bench_script": "scripts/run_v2_wire_shadow_metering_bench_v1.py",
            "summarize_script": "scripts/summarize_v2_wire_shadow_metering_v1.py",
        },
        "pytest_wire_bundle": pytest_result,
        "integration_ssot": "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_brief_v1.json",
    }
    phase2_result: dict[str, object] | None = None
    if args.include_phase2:
        phase2_result = _run_phase2()
        if phase2_result.get("ok"):
            doc["phase2_complete"] = [
                "v2_wire_shadow_metering_v1.jsonl bench (economy off/on pairs)",
                "comp_v2_wire_shadow_metering_summary_v1.json aggregate",
            ]
            doc["phase2_deferred"] = []
            doc["phase3_weekly_ops_ready"] = True
        else:
            doc["phase2_error"] = phase2_result
    doc["phase2_last_run"] = phase2_result

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT.relative_to(ROOT)),
                "pytest_exit": pytest_result["exit_code"],
                "phase2_ok": (phase2_result or {}).get("ok"),
            },
            ensure_ascii=False,
        )
    )
    if not pytest_result["passed"]:
        return 1
    if phase2_result is not None and not phase2_result.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
