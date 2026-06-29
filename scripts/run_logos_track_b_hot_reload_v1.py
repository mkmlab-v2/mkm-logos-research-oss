#!/usr/bin/env python3
"""Hot-reload loop — run Phase O, score completion, re-run until target [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_track_b_hot_reload_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 900, verbose: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    if verbose:
        print(f"\n[hot-reload] >>> {name}", flush=True)
        proc = subprocess.run(cmd, cwd=ROOT, timeout=timeout)
        stdout_tail = ""
        stderr_tail = ""
    else:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        stdout_tail = (proc.stdout or "")[-300:]
        stderr_tail = (proc.stderr or "")[-200:]
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "ok": proc.returncode == 0,
    }


def _load_completion() -> dict[str, Any]:
    path = REPORTS / "logos_phase_o_completion_gate_v1_latest.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--max-iterations", type=int, default=3)
    ap.add_argument("--min-score", type=float, default=90.0)
    ap.add_argument("--verbose", action="store_true", help="Stream child stdout (progress visible)")
    ap.add_argument("--quiet", action="store_true", help="Suppress operator board print")
    args = ap.parse_args()

    iterations: list[dict[str, Any]] = []
    all_steps: list[dict[str, Any]] = []
    final_score = 0.0
    passed = False

    phase_o_cmd = [PY, "scripts/run_logos_track_b_phase_o_v1.py", "--skip-registry", "--skip-closure"]

    for i in range(1, args.max_iterations + 1):
        step = _run(f"phase_o_iter_{i}", phase_o_cmd, verbose=args.verbose)
        all_steps.append(step)
        completion = _load_completion()
        score = float(completion.get("completion_score") or 0)
        final_score = score
        iter_ok = step["ok"] and completion.get("completion_pass") is True
        iterations.append(
            {
                "iteration": i,
                "completion_score": score,
                "failed_checks": (completion.get("summary") or {}).get("failed_checks") or [],
                "ok": iter_ok,
            }
        )
        if iter_ok and score >= args.min_score:
            passed = True
            break

    if passed:
        all_steps.append(
            _run("reasoning_registry", [PY, "scripts/build_logos_reasoning_pattern_registry_v1.py"], verbose=args.verbose)
        )
        all_steps.append(
            _run("integration_closure", [PY, "scripts/build_logos_track_b_integration_closure_v1.py"], verbose=args.verbose)
        )

    board_proc = subprocess.run(
        [PY, "scripts/build_logos_hot_reload_operator_board_v1.py", "--print"],
        cwd=ROOT,
        capture_output=not args.verbose,
        text=True,
        timeout=60,
    )
    board_path = REPORTS / "logos_hot_reload_operator_board_v1_latest.md"

    doc = {
        "schema": "logos_track_b_hot_reload_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "hot_reload": True,
        "max_iterations": args.max_iterations,
        "min_score": args.min_score,
        "iterations_run": len(iterations),
        "final_completion_score": final_score,
        "completion_pass": passed,
        "iterations": iterations,
        "steps": all_steps,
        "artifacts": {
            "operator_board_md": "reports/logos_hot_reload_operator_board_v1_latest.md",
            "phase_o": "reports/logos_track_b_phase_o_v1_latest.json",
            "completion_gate": "reports/logos_phase_o_completion_gate_v1_latest.json",
            "digest_md": "reports/logos_phase_o_digest_v1_latest.md",
        },
        "ok": passed,
        "reproduce": "py scripts/run_logos_track_b_hot_reload_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.quiet and board_proc.stdout:
        print("\n" + "=" * 60, flush=True)
        print(board_proc.stdout, flush=True)
        print("=" * 60, flush=True)
    print(
        json.dumps(
            {
                "ok": passed,
                "iterations": len(iterations),
                "completion_score": final_score,
                "operator_board": str(board_path),
                "digest_md": str(REPORTS / "logos_phase_o_digest_v1_latest.md"),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
