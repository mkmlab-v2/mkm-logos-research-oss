#!/usr/bin/env python3
"""[HYPO] DR Phase 8 — Path A masked cohort + Judges/chasm ablation + closure refresh.

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
OUT = ROOT / "reports/ng40_dr_phase8_customer_judges_completion_chain_v1_latest.json"
PATH_A_CHAIN = ROOT / "reports/ng40_path_a_customer_masked_cohort_chain_v1_latest.json"
JUDGES_ABLATION = ROOT / "reports/compression_judges_chasm_corpus_conditional_ablation_v1_latest.json"


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
    ap.add_argument("--rows", type=int, default=25)
    ap.add_argument("--skip-path-a", action="store_true")
    ap.add_argument("--skip-judges-chasm", action="store_true")
    ap.add_argument("--skip-closure-refresh", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_path_a:
        steps.append(
            _run(
                "path_a_customer_masked_cohort",
                [PY, "scripts/run_ng40_path_a_customer_masked_cohort_chain_v1.py", "--rows", str(args.rows)],
            )
        )

    if not args.skip_judges_chasm:
        steps.append(
            _run("judges_chasm_ablation", [PY, "scripts/run_compression_judges_chasm_corpus_conditional_ablation_v1.py"])
        )

    if not args.skip_closure_refresh:
        steps.append(_run("dr_closure_refresh", [PY, "scripts/build_compression_multilens_dr_closure_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_phase8_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "-q",
                    "tests/test_ng40_path_a_customer_masked_cohort_chain_v1.py",
                    "tests/test_compression_judges_chasm_corpus_conditional_ablation_v1.py",
                ],
            )
        )

    path_a = _load(str(PATH_A_CHAIN.relative_to(ROOT)).replace("\\", "/"))
    judges = _load(str(JUDGES_ABLATION.relative_to(ROOT)).replace("\\", "/"))
    closure = _load("reports/compression_multilens_dr_closure_v1_latest.json")

    chain_ok = all(s["exit_code"] == 0 for s in steps)

    report = {
        "schema": "ng40_dr_phase8_customer_judges_completion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "chain_ok": chain_ok,
        "steps": steps,
        "path_a_customer_cohort": {
            "pointer": str(PATH_A_CHAIN.relative_to(ROOT)).replace("\\", "/"),
            "chain_ok": (path_a or {}).get("chain_ok"),
            "spine_invariant": (path_a or {}).get("path_a_spine_eval", {}).get("spine_byte_exact_ok"),
            "spine_saving": (path_a or {}).get("path_a_spine_eval", {}).get("global_token_saving_rate_spine_binary"),
        },
        "judges_chasm_ablation": {
            "pointer": str(JUDGES_ABLATION.relative_to(ROOT)).replace("\\", "/"),
            "policy_counts": (judges or {}).get("policy_counts"),
            "conditional_saving": (judges or {}).get("arms", {}).get("conditional_merged", {}).get(
                "mean_token_saving_rate_proxy"
            ),
        },
        "phase7_pointer": "reports/ng40_dr_phase7_master_closure_chain_v1_latest.json",
        "closure_pointer": "reports/compression_multilens_dr_closure_v1_latest.json",
        "stack_closure_ok": (closure or {}).get("stack_closure_ok"),
        "verdict_ko": [
            "Phase8: Path A masked cohort spine invariant + ROI proxy",
            "Judges/chasm domain-conditional ablation — research only",
        ],
        "reproducible_command": "py scripts/run_ng40_dr_phase8_customer_judges_completion_chain_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": chain_ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
