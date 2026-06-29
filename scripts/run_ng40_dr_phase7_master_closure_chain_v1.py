#!/usr/bin/env python3
"""[HYPO] DR Phase 7 — master closure rollup + full DR pytest bundle.

Default: verify phase2–6 artifacts on disk + build closure (no heavy codec rerun).
research_only · send_gate HOLD · never --apply-active.
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
PY = sys.executable
OUT = ROOT / "reports/ng40_dr_phase7_master_closure_chain_v1_latest.json"
CLOSURE = ROOT / "reports/compression_multilens_dr_closure_v1_latest.json"

DR_PYTEST = [
    "tests/test_compression_conditional_fusion_ablation_v1.py",
    "tests/test_compression_conditional_fusion_ablation_v2_codec_rerun_v1.py",
    "tests/test_compression_conditional_fusion_ablation_v3_ssot_guard_v1.py",
    "tests/test_compression_hybrid_router_v3_wire_v1.py",
    "tests/test_compression_conditional_fusion_pareto_research_signoff_v1.py",
    "tests/test_compression_token_api_v2_stub.py::test_compress_corpus_tag_golden40_conditional_fusion_v3_binding",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh-phase6", action="store_true", help="Re-run phase6 chain before closure")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-closure", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if args.refresh_phase6:
        steps.append(
            _run("phase6_refresh", [PY, "scripts/run_ng40_dr_phase6_stub_pareto_completion_chain_v1.py"])
        )

    if not args.skip_closure:
        steps.append(_run("build_dr_closure", [PY, "scripts/build_compression_multilens_dr_closure_v1.py"]))

    if not args.skip_pytest:
        steps.append(_run("pytest_dr_bundle", [PY, "-m", "pytest", "-q", *DR_PYTEST]))

    closure = _load(str(CLOSURE.relative_to(ROOT)).replace("\\", "/"))
    chain_ok = all(s["exit_code"] == 0 for s in steps) and bool((closure or {}).get("stack_closure_ok"))

    report = {
        "schema": "ng40_dr_phase7_master_closure_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "chain_ok": chain_ok,
        "steps": steps,
        "stack_closure_ok": (closure or {}).get("stack_closure_ok"),
        "phase_chain_status": (closure or {}).get("phases"),
        "recommended_research_headline": (closure or {}).get("pareto_signoff", {}).get(
            "recommended_research_headline_arm"
        ),
        "conflict_surface": (closure or {}).get("conflict_surface"),
        "artifacts": {
            "closure": str(CLOSURE.relative_to(ROOT)).replace("\\", "/"),
            "pareto_signoff": "reports/compression_conditional_fusion_pareto_research_signoff_v1_latest.json",
            "v3_ablation": "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json",
            "hybrid_spec": "docs/final/artifacts/compression_hybrid_router_spec_v1.json",
            "lit_review": "docs/research/COMPRESSION_IMPROVEMENT_MULTILENS_DEEP_RESEARCH_LIT_REVIEW_2026-06-22.md",
        },
        "verdict_ko": [
            "Phase7: DR Phase2–6 master closure + pytest bundle",
            "stack_closure_ok = 모든 phase chain_ok + closure artifact",
        ],
        "reproducible_command": "py scripts/run_ng40_dr_phase7_master_closure_chain_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": chain_ok, "stack_closure_ok": report["stack_closure_ok"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
