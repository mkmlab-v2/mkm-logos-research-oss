#!/usr/bin/env python3
"""[HYPO] DR Phase 6 — stub binding + Pareto research signoff + pytest.

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
OUT = ROOT / "reports/ng40_dr_phase6_stub_pareto_completion_chain_v1_latest.json"
PARETO_SIGNOFF = ROOT / "reports/compression_conditional_fusion_pareto_research_signoff_v1_latest.json"


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
    ap.add_argument("--skip-pareto-signoff", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--no-human-approve-research", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_pareto_signoff:
        signoff_cmd = [
            PY,
            "scripts/build_compression_conditional_fusion_pareto_research_signoff_v1.py",
        ]
        if not args.no_human_approve_research:
            signoff_cmd.extend(["--human-approve-research", "--reviewer", "commander"])
        steps.append(_run("pareto_research_signoff", signoff_cmd))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_stub_pareto_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_compression_token_api_v2_stub.py::test_compress_corpus_tag_golden40_conditional_fusion_v3_binding",
                    "tests/test_compression_hybrid_router_v3_wire_v1.py",
                    "tests/test_compression_conditional_fusion_ablation_v3_ssot_guard_v1.py",
                ],
            )
        )

    chain_ok = all(s["exit_code"] == 0 for s in steps)
    pareto = _load(str(PARETO_SIGNOFF.relative_to(ROOT)).replace("\\", "/"))
    phase5 = _load("reports/ng40_dr_phase5_hybrid_v3_wire_completion_chain_v1_latest.json")

    report = {
        "schema": "ng40_dr_phase6_stub_pareto_completion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "chain_ok": chain_ok,
        "steps": steps,
        "stub_pareto_stack": {
            "golden40_stub_backend": "mkm_conditional_fusion_v3_ssot_guard",
            "pareto_recommended_arm": (pareto or {}).get("recommended_research_headline_arm"),
            "pareto_front": (pareto or {}).get("pareto_front_arm_ids"),
            "commander_research_approval": (pareto or {}).get("commander_research_approval"),
            "apply_active_forbidden": True,
            "beat_frozen": (pareto or {}).get("beat_frozen"),
        },
        "phase5_pointer": "reports/ng40_dr_phase5_hybrid_v3_wire_completion_chain_v1_latest.json",
        "phase5_chain_ok": (phase5 or {}).get("chain_ok"),
        "artifacts": {
            "pareto_signoff": str(PARETO_SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "hybrid_spec": "docs/final/artifacts/compression_hybrid_router_spec_v1.json",
            "v3_ablation": "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json",
        },
        "verdict_ko": [
            "Phase6: golden40 stub → conditional fusion v3 research lane (200 + integrity flags)",
            "Pareto signoff: knee_j + v3 SSOT research headline — ACTIVE apply 금지",
        ],
        "reproducible_command": "py scripts/run_ng40_dr_phase6_stub_pareto_completion_chain_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": chain_ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
