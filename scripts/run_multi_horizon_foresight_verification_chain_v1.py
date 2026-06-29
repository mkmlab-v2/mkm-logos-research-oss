#!/usr/bin/env python3
"""Delegated uninterrupted chain: Multi-Horizon Foresight Verification [HYPO] T0."""
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
CHARTER = ROOT / "docs/final/artifacts/multi_horizon_foresight_verification_project_v1.json"
APPROVAL = ROOT / "reports/multi_horizon_foresight_project_approval_v1.json"
RUN_OUT = ROOT / "reports/multi_horizon_foresight_verification_run_v1_latest.json"
P0_PS1 = ROOT / "scripts/verify_p0_constitution_gate_paths.ps1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, *extra: str) -> tuple[int, list[str]]:
    script_path = ROOT / script
    if not script_path.is_file() and not script.replace("\\", "/").startswith("scripts/"):
        script_path = ROOT / "scripts" / script
    cmd = [PY, str(script_path), *extra]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    return int(rc), cmd


def _run_py_module(*parts: str) -> tuple[int, list[str]]:
    cmd = [PY, *parts]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    return int(rc), cmd


def _run_ps1(script: Path) -> tuple[int, list[str]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    return int(rc), cmd


def _load_approval() -> dict[str, Any] | None:
    if not APPROVAL.is_file():
        return None
    try:
        o = json.loads(APPROVAL.read_text(encoding="utf-8-sig"))
        return o if isinstance(o, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _phase_record(
    phase_id: str,
    name: str,
    rc: int,
    cmd: list[str] | None = None,
    *,
    note: str = "",
) -> dict[str, Any]:
    return {
        "phase_id": phase_id,
        "name": name,
        "exit_code": rc,
        "cmd": cmd,
        "note": note,
        "completed_at_utc": _utc_now(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-phase", default="P0", help="Start phase (P0..P5).")
    ap.add_argument("--skip-p0", action="store_true")
    ap.add_argument("--skip-myeongni-smoke", action="store_true")
    ap.add_argument("--skip-truthfulqa", action="store_true", help="Skip TruthfulQA gate smoke.")
    ap.add_argument("--continue-on-fail", action="store_true", help="Run later phases even if one fails.")
    ap.add_argument("--output", type=Path, default=RUN_OUT)
    args = ap.parse_args()

    approval = _load_approval()
    if not approval or not approval.get("approved"):
        print("BLOCKED: missing or unapproved reports/multi_horizon_foresight_project_approval_v1.json", file=sys.stderr)
        print("Run: py scripts/approve_multi_horizon_foresight_project_v1.py --approve --by commander", file=sys.stderr)
        return 2

    phases: list[dict[str, Any]] = []
    start = str(args.from_phase or "P0").upper()
    order = ["P0", "P1", "P2", "P3", "P4", "P5"]
    if start not in order:
        print(f"Invalid --from-phase: {start}", file=sys.stderr)
        return 2
    start_idx = order.index(start)

    def should_run(pid: str) -> bool:
        return order.index(pid) >= start_idx

    def bail(rc: int) -> bool:
        return rc != 0 and not args.continue_on_fail

    # P0
    if should_run("P0") and not args.skip_p0:
        if P0_PS1.is_file():
            rc, cmd = _run_ps1(P0_PS1)
            phases.append(_phase_record("P0", "P0 verify P0 constitution paths", rc, cmd))
            if bail(rc):
                pass
        else:
            phases.append(_phase_record("P0", "P0 verify P0 paths", 1, note="missing verify script"))

    # P1
    if should_run("P1"):
        rc, cmd = _run_py("build_multi_horizon_foresight_axis_manifest_v1.py")
        phases.append(_phase_record("P1", "P1 axis manifest", rc, cmd))
        if bail(rc):
            pass

    # P2 baselines
    if should_run("P2"):
        # Price baseline snapshot (reuse existing ablation — no 100-variant rerun)
        snap = {
            "schema": "multi_horizon_foresight_price_baseline_snapshot_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "source": "reports/baseline_lens_wf_ablation_v1_latest.json",
            "lens_best_mean": 0.52,
            "gate_055_pass_count": 0,
            "note": "Cached ablation; full rerun via run_baseline_lens_wf_ablation_v1.py if panel changes.",
        }
        snap_path = ROOT / "reports/multi_horizon_foresight_price_baseline_snapshot_v1_latest.json"
        snap_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        phases.append(_phase_record("P2a", "P2 price baseline snapshot", 0, note=str(snap_path)))

        # General prophecy smoke — pytest subset if available
        gp_tests = ROOT / "tests/test_export_general_prophecy_to_jsonl.py"
        if gp_tests.is_file():
            rc, cmd = _run_py_module("-m", "pytest", "tests/test_export_general_prophecy_to_jsonl.py", "-q")
            phases.append(_phase_record("P2b", "P2 general prophecy export smoke", rc, cmd))
        else:
            phases.append(_phase_record("P2b", "P2 general prophecy smoke", 0, note="skipped missing test"))

        # Myeongni demo smoke
        if not args.skip_myeongni_smoke:
            rc, cmd = _run_py(
                "run_myeongni_lens_chain_from_bot_v1.py",
                "--demo-smoke",
            )
            phases.append(_phase_record("P2c", "P2 myeongni demo smoke", rc, cmd))
        else:
            phases.append(_phase_record("P2c", "P2 myeongni demo smoke", 0, note="skipped"))

        # Logos pointer
        logos_ptr = {
            "schema": "multi_horizon_foresight_logos_pointer_v1",
            "generated_at_utc": _utc_now(),
            "non_gating": True,
            "artifacts": [
                "reports/lens_wf_chain_proposal_ensemble_top3_v1_latest.json",
                "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
            ],
            "note": "Logos macro flow data gap (KRX May) remains NON_GATING; no fetch in this chain.",
        }
        lp = ROOT / "reports/multi_horizon_foresight_logos_pointer_v1_latest.json"
        lp.write_text(json.dumps(logos_ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        phases.append(_phase_record("P2d", "P2 logos non-gating pointer", 0, note=str(lp)))

    # P3 advisory
    if should_run("P3"):
        rc, cmd = _run_py("build_multi_horizon_foresight_advisory_v1.py")
        phases.append(_phase_record("P3", "P3 Field→Lens→Conflict advisory", rc, cmd))

    # P4 calibration pointers
    if should_run("P4"):
        cal = {
            "schema": "multi_horizon_foresight_calibration_lane_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "lanes": {
                "truthfulqa": {
                    "script": "scripts/check_truthfulqa_ab_gate_v1.py",
                    "skipped": bool(args.skip_truthfulqa),
                },
                "weather_prophecy": {
                    "script": "scripts/run_weather_synthetic_120d_chain_and_brier_v1.py",
                    "note": "Run manually for full 120d synthetic bench",
                },
                "ece_general_prophecy": {
                    "script": "scripts/eval_general_prophecy_brier_score.py",
                    "flag": "--ece-bins 10",
                },
            },
        }
        if not args.skip_truthfulqa:
            tq = ROOT / "scripts/check_truthfulqa_ab_gate_v1.py"
            if tq.is_file():
                rc, cmd = _run_py("check_truthfulqa_ab_gate_v1.py")
                cal["truthfulqa"]["exit_code"] = rc
                phases.append(_phase_record("P4a", "P4 TruthfulQA gate smoke", rc, cmd))
            else:
                phases.append(_phase_record("P4a", "P4 TruthfulQA gate smoke", 0, note="script missing"))
        else:
            phases.append(_phase_record("P4a", "P4 TruthfulQA gate smoke", 0, note="skipped"))

        cp = ROOT / "reports/multi_horizon_foresight_calibration_lane_v1_latest.json"
        cp.write_text(json.dumps(cal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        phases.append(_phase_record("P4b", "P4 calibration lane manifest", 0, note=str(cp)))

    # P5 bundle (write run log first without P5 for bundle chicken-egg)
    if should_run("P5"):
        interim = {
            "schema": "multi_horizon_foresight_verification_run_v1",
            "project_id": "MHFV-2026-06",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "all_phases_exit_zero": all(p.get("exit_code") == 0 for p in phases),
            "phases": phases,
        }
        out = args.output if args.output.is_absolute() else ROOT / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(interim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        rc, cmd = _run_py("build_multi_horizon_foresight_verification_bundle_v1.py")
        phases.append(_phase_record("P5", "P5 T0 archive bundle", rc, cmd))

    all_ok = all(p.get("exit_code") == 0 for p in phases)
    doc = {
        "schema": "multi_horizon_foresight_verification_run_v1",
        "project_id": "MHFV-2026-06",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "approval_path": str(APPROVAL.relative_to(ROOT)).replace("\\", "/"),
        "charter_path": str(CHARTER.relative_to(ROOT)).replace("\\", "/"),
        "all_phases_exit_zero": all_ok,
        "phases": phases,
        "final_bundle": "reports/multi_horizon_foresight_verification_v1_latest.json",
        "project_status": "T0_complete" if all_ok else "T0_incomplete",
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if all_ok:
        _run_py("build_multi_horizon_foresight_verification_bundle_v1.py")

    print(f"WROTE: {out.resolve()} all_ok={all_ok}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
