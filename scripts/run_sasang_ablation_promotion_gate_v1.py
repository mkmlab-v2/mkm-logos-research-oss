#!/usr/bin/env python3
"""Sasang ablation B-track promotion gate — SPEC-MKM-2026-06A.

Orchestrates build/test/signoff with commander-preapproved B-track merge only.

  py scripts/run_sasang_ablation_promotion_gate_v1.py --commander-ack
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
EXP = ROOT / "experiments" / "sasang-head-btrack"
ART = EXP / "artifacts"
DEFAULT_BASELINE = Path(r"C:\workspace\reports\mkm_ltm_route_accuracy_bench_v1_latest.json")
SIGNOFF = ROOT / "reports/sasang_ablation_matrix_signoff_v1.json"
PAPER_VERDICT = ART / "sasang_pyobyeong_promotion_paper_verdict_v1.json"
CHARTER = EXP / "CHARTER_AMENDMENT_DRAFT_v1.md"
OUT_REPORT = ART / "sasang_ablation_promotion_gate_v1_latest.json"

STEPS: list[tuple[str, list[str]]] = [
    ("build_pyobyeong_dr_pack", [sys.executable, "scripts/build_ijeoma_pyobyeong_dr_pack_v1.py"]),
    ("unified_adapter", [sys.executable, "scripts/run_sasang_dynamics_unified_adapter_v1.py"]),
    (
        "ablation_bench",
        [
            sys.executable,
            "scripts/run_lens_sasang_ablation_bench_v1.py",
            "--baseline-report",
            str(DEFAULT_BASELINE),
            "--skip-target-bench",
        ],
    ),
    (
        "pytest",
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_ijeoma_pyobyeong_dr_pack_v1.py",
            "tests/test_sasang_dynamics_unified_adapter_v1.py",
            "tests/test_lens_sasang_ablation_bench_v1.py",
            "-q",
        ],
    ),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    return {
        "step": name,
        "command": " ".join(cmd),
        "exit_code": int(cp.returncode),
        "stdout_tail": (cp.stdout or "").strip()[-500:],
        "stderr_tail": (cp.stderr or "").strip()[-500:],
    }


def _load_signoff() -> dict[str, Any]:
    return json.loads(SIGNOFF.read_text(encoding="utf-8"))


def _promotion_checks(commander_ack: bool) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["charter_amendment_present"] = CHARTER.is_file()
    checks["paper_verdict_present"] = PAPER_VERDICT.is_file()
    checks["unified_adapter_artifact"] = (ART / "sasang_dynamics_unified_ablation_v1.json").is_file()
    checks["pyobyeong_cards_ablation"] = (ART / "ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json").is_file()
    checks["commander_ack"] = commander_ack
    if PAPER_VERDICT.is_file():
        pv = json.loads(PAPER_VERDICT.read_text(encoding="utf-8"))
        promo = (pv.get("slots") or {}).get("promotion") or {}
        checks["paper_promotion_merge_allowed"] = promo.get("merge_allowed") is True
        checks["paper_track_a_blocked"] = promo.get("track_a_promotion_allowed") is False
    signoff = _load_signoff() if SIGNOFF.is_file() else {}
    gates = signoff.get("gates") or {}
    checks["ltm_parity"] = gates.get("ltm_graph_top1_parity") is True
    checks["citation_lock"] = gates.get("citation_lock_intact") is True
    checks["static_non_gating"] = gates.get("static_non_gating_verified") is True
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commander-ack", action="store_true", help="Commander pre-approved B-track merge")
    ap.add_argument("--skip-steps", action="store_true", help="Only evaluate gates from existing artifacts")
    args = ap.parse_args()

    if not args.commander_ack:
        print(json.dumps({"ok": False, "error": "requires --commander-ack"}))
        return 2

    step_results: list[dict[str, Any]] = []
    if not args.skip_steps:
        for name, cmd in STEPS:
            step_results.append(_run_step(name, cmd))
            if step_results[-1]["exit_code"] != 0:
                break

    checks = _promotion_checks(args.commander_ack)
    steps_ok = all(s["exit_code"] == 0 for s in step_results) if step_results else True
    checks_ok = all(
        checks.get(k)
        for k in (
            "charter_amendment_present",
            "paper_verdict_present",
            "unified_adapter_artifact",
            "pyobyeong_cards_ablation",
            "commander_ack",
            "paper_promotion_merge_allowed",
            "paper_track_a_blocked",
            "ltm_parity",
            "citation_lock",
            "static_non_gating",
        )
    )

    promotion_ready = steps_ok and checks_ok

    if SIGNOFF.is_file():
        signoff = _load_signoff()
        signoff["generated_at_utc"] = _utc()
        signoff["merge_allowed"] = promotion_ready
        signoff["promotion_ready"] = promotion_ready
        signoff["commander_preapproved"] = True
        signoff["track_a_promotion_allowed"] = False
        signoff["send_gate"] = "HOLD"
        if promotion_ready:
            signoff["gates"]["charter_amendment_required_before_merge"] = False
            signoff["gates"]["b_track_merge_approved"] = True
        signoff["promotion_artifacts"] = {
            "paper_verdict": str(PAPER_VERDICT.relative_to(ROOT)).replace("\\", "/"),
            "charter_amendment": str(CHARTER.relative_to(ROOT)).replace("\\", "/"),
            "unified_adapter": "experiments/sasang-head-btrack/artifacts/sasang_dynamics_unified_ablation_v1.json",
            "pyobyeong_insight_cards": "experiments/sasang-head-btrack/artifacts/ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json",
        }
        SIGNOFF.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": "sasang_ablation_promotion_gate_v1",
        "generated_at_utc": _utc(),
        "promotion_ready": promotion_ready,
        "merge_allowed": promotion_ready,
        "track_a_promotion_allowed": False,
        "send_gate": "HOLD",
        "steps": step_results,
        "checks": checks,
        "signoff": str(SIGNOFF).replace("\\", "/"),
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": promotion_ready, "promotion_ready": promotion_ready, "report": str(OUT_REPORT)}))
    return 0 if promotion_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
