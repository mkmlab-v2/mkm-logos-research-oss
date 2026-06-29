#!/usr/bin/env python3
"""RQ-026 one-click: sim(v1_1 default) → phase2 → phase4 → matrix promotion → signoff."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-days", type=int, default=0)
    ap.add_argument("--skip-signoff", action="store_true")
    ap.add_argument("--skip-phase4", action="store_true", help="omit holdout ablation step")
    ap.add_argument(
        "--skip-matrix-promotion-record",
        action="store_true",
        help="omit promotion artifact refresh",
    )
    args = ap.parse_args()

    sim_cmd = [PY, str(ROOT / "scripts/run_sasang_temperament_agents_sim_stub_v1.py")]
    if args.max_days > 0:
        sim_cmd.extend(["--max-days", str(args.max_days)])

    steps: list[tuple[str, list[str]]] = [
        ("sim_matrix_coupled_v1_2", sim_cmd),
        (
            "phase2_eval",
            [
                PY,
                str(ROOT / "scripts/build_sasang_temperament_agents_phase2_eval_v1.py"),
                "--also-artifact",
                "--strict",
            ],
        ),
    ]
    if not args.skip_phase4:
        steps.append(
            (
                "phase4_holdout_ablation",
                [
                    PY,
                    str(ROOT / "scripts/build_sasang_temperament_agents_phase4_holdout_ablation_v1.py"),
                    "--also-report",
                    "--strict",
                ],
            )
        )
    steps.append(
        (
            "narrative_lint",
            [PY, str(ROOT / "scripts/lint_rq026_narrative_fact_lock_v1.py"), "--strict"],
        )
    )
    if not args.skip_matrix_promotion_record:
        steps.append(
            (
                "matrix_v1_2_promotion_record",
                [PY, str(ROOT / "scripts/record_rq026_pathology_matrix_v1_2_promotion_v1.py")],
            )
        )
    if not args.skip_signoff:
        steps.append(
            (
                "commander_signoff",
                [PY, str(ROOT / "scripts/record_rq026_commander_btrack_signoff_v1.py")],
            )
        )

    results: list[dict[str, Any]] = []
    for name, cmd in steps:
        r = _run(cmd)
        r["name"] = name
        results.append(r)
        if r["exit_code"] != 0:
            print(json.dumps({"ok": False, "failed_step": name, "results": results}, ensure_ascii=False))
            return r["exit_code"]

    print(
        json.dumps(
            {"ok": True, "steps": [s["name"] for s in results], "n_steps": len(results)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
