#!/usr/bin/env python3
"""Run M1→M2→M3 compression hardening milestones (parallel subprocesses)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ART / "compression_hardening_milestone_status_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(label: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "step": label,
        "exit_code": proc.returncode,
        "stderr_tail": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-tier-check", action="store_true")
    ap.add_argument("--skip-bench-smoke", action="store_true")
    ap.add_argument("--skip-demo", action="store_true", help="Skip demo_token_api_modes (needs uvicorn).")
    args = ap.parse_args()

    py = sys.executable
    demo_cmd = (
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/demo_token_api_modes.ps1"),
        ]
        if sys.platform == "win32"
        else [py, str(ROOT / "scripts/demo_token_api_modes.ps1")]
    )
    jobs = [
        ("M1_pytest_hardening", [py, "-m", "pytest", "tests/test_compression_hardening_v1.py", "-q", "--tb=no"]),
    ]
    if not args.skip_demo:
        jobs.append(("M2_demo_modes", demo_cmd))
    if args.skip_pytest:
        jobs = [j for j in jobs if "pytest" not in j[0]]

    parallel = [
        ("M3_codebook_hash", [py, str(ROOT / "scripts/verify_codebook_manifest_hash_v1.py")]),
        ("M2_tier_check", [py, str(ROOT / "scripts/check_compression_domain_adoption_tier_v1.py")]),
    ]
    if args.skip_tier_check:
        parallel = [p for p in parallel if p[0] != "M2_tier_check"]
    if not args.skip_bench_smoke:
        parallel.append(
            (
                "M1_bench_smoke",
                [
                    py,
                    str(ROOT / "scripts/run_ultra_compression_default.py"),
                    "--mode",
                    "universal",
                ],
            )
        )

    steps: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(4, len(parallel))) as pool:
        futs = {pool.submit(_run, label, cmd): label for label, cmd in parallel}
        for fut in as_completed(futs):
            steps.append(fut.result())

    for label, cmd in jobs:
        steps.append(_run(label, cmd))

    failed = [s["step"] for s in steps if s.get("exit_code", 1) != 0]
    milestones = {
        "M0_baseline": {"ms_submission": "complete", "rag_l3_local": True},
        "M1_quick_wins": {
            "gatekeeper_config": str(ART / "compression_enterprise_hardening_config_v1.json"),
            "passed": "M1_pytest_hardening" not in failed,
        },
        "M2_circuit_gatekeeper": {
            "stub_wired": True,
            "passed": ("M2_demo_modes" not in failed) if not args.skip_demo else True,
            "demo_skipped": bool(args.skip_demo),
        },
        "M3_enterprise": {
            "native_plan": str(ART / "compression_native_core_migration_plan_m3_v1.json"),
            "codebook_manifest": str(ART / "codebook_manifest_hashes_v1_latest.json"),
            "passed": "M3_codebook_hash" not in failed,
        },
    }
    doc = {
        "schema": "compression_hardening_milestone_status_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "ok": not failed,
        "failed_steps": failed,
        "steps": sorted(steps, key=lambda x: str(x.get("step"))),
        "milestones": milestones,
        "track_wall": {
            "track_a_live_trading": False,
            "prophecy_promotion_gates_touch": False,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not failed, "failed": failed, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
