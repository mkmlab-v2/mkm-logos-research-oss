#!/usr/bin/env python3
"""Hot-reload Sasang-41k — tune mismatch threshold, minimize rate, keep gate pass [HYPO]."""

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
OUT_DEFAULT = REPORTS / "btrack_sasang_41k_hot_reload_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 180) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--max-iterations", type=int, default=4)
    ap.add_argument("--max-mismatch-rate", type=float, default=0.75)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    thresholds = [0.45, 0.50, 0.55, 0.60][: max(1, args.max_iterations)]
    iterations: list[dict[str, Any]] = []
    all_steps: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for i, th in enumerate(thresholds, start=1):
        iter_steps: list[dict[str, Any]] = []
        iter_steps.append(
            _run(
                f"shadow_iter_{i}",
                [
                    PY,
                    "scripts/build_btrack_sasang_lexicon_shadow_v1.py",
                    "--mismatch-threshold",
                    str(th),
                ],
            )
        )
        iter_steps.append(
            _run(
                f"gate_iter_{i}",
                [
                    PY,
                    "scripts/build_btrack_sasang_role_mismatch_gate_v1.py",
                    "--max-mismatch-rate",
                    str(args.max_mismatch_rate),
                ],
            )
        )
        all_steps.extend(iter_steps)
        shadow = _load(REPORTS / "btrack_sasang_lexicon_shadow_v1_latest.json")
        gate = _load(REPORTS / "btrack_sasang_role_mismatch_gate_v1_latest.json")
        rate = float((shadow.get("mismatch_summary") or {}).get("mismatch_rate") or 1.0)
        gate_pass = (gate.get("summary") or {}).get("gate_pass") is True
        row = {
            "iteration": i,
            "mismatch_threshold": th,
            "mismatch_rate": rate,
            "gate_pass": gate_pass,
            "ok": all(s.get("ok") for s in iter_steps) and gate_pass,
        }
        iterations.append(row)
        if row["ok"] and (best is None or rate < float(best["mismatch_rate"])):
            best = row
        if args.verbose:
            print(json.dumps(row, ensure_ascii=False), flush=True)

    if best is None:
        best = iterations[-1] if iterations else {"mismatch_threshold": 0.55}

    apply_steps: list[dict[str, Any]] = []
    apply_steps.append(
        _run(
            "shadow_apply_best",
            [
                PY,
                "scripts/build_btrack_sasang_lexicon_shadow_v1.py",
                "--mismatch-threshold",
                str(best["mismatch_threshold"]),
            ],
        )
    )
    apply_steps.append(
        _run(
            "gate_apply_best",
            [
                PY,
                "scripts/build_btrack_sasang_role_mismatch_gate_v1.py",
                "--max-mismatch-rate",
                str(args.max_mismatch_rate),
            ],
        )
    )
    apply_steps.append(_run("psi_bridge", [PY, "scripts/build_btrack_sasang_psi_role_bridge_v1.py"]))
    apply_steps.append(_run("completion_gate", [PY, "scripts/build_btrack_sasang_41k_completion_gate_v1.py"]))
    apply_steps.append(_run("operator_board", [PY, "scripts/build_btrack_sasang_41k_operator_board_v1.py"]))
    all_steps.extend(apply_steps)

    shadow = _load(REPORTS / "btrack_sasang_lexicon_shadow_v1_latest.json")
    completion = _load(REPORTS / "btrack_sasang_41k_completion_gate_v1_latest.json")
    psi_bridge = _load(REPORTS / "btrack_sasang_psi_role_bridge_v1_latest.json")

    overall_ok = (
        all(s.get("ok") for s in all_steps)
        and completion.get("completion_pass") is True
        and psi_bridge.get("bridge_ok") is True
    )

    doc = {
        "schema": "btrack_sasang_41k_hot_reload_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_bridge": False,
        "iterations_run": len(iterations),
        "best_iteration": best,
        "final_mismatch_rate": (shadow.get("mismatch_summary") or {}).get("mismatch_rate"),
        "completion_score": completion.get("completion_score"),
        "completion_pass": completion.get("completion_pass"),
        "psi_bridge_ok": psi_bridge.get("bridge_ok"),
        "ok": overall_ok,
        "iterations": iterations,
        "steps": all_steps,
        "reproduce_cmd": "py scripts/run_btrack_sasang_41k_hot_reload_v1.py --verbose",
        "operator_board": "reports/btrack_sasang_41k_operator_board_v1_latest.md",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.verbose:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "ok": overall_ok,
                    "best_threshold": best.get("mismatch_threshold"),
                    "mismatch_rate": doc["final_mismatch_rate"],
                    "completion_score": doc["completion_score"],
                },
                ensure_ascii=False,
            )
        )
    if overall_ok:
        print(f"\nOpen: {doc['operator_board']}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
