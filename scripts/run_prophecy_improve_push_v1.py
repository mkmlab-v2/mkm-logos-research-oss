#!/usr/bin/env python3
"""[HYPO] Push B-track prophecy metrics until strict/combined gates pass or max rounds.

No live trading. Does not set Track A live GO without human sign-off.
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
OUT = ROOT / "reports/prophecy_improve_push_v1_latest.json"
GATES = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
READINESS = ROOT / "reports/prophecy_promotion_readiness_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _gate_snapshot() -> dict[str, Any]:
    g = _load(GATES)
    r = _load(READINESS)
    return {
        "combined_all_passed": bool(g.get("combined_all_passed")),
        "strict_passed": bool(g.get("strict_passed")),
        "soft_passed": bool(g.get("soft_passed")),
        "auto_promote_ready": bool(g.get("auto_promote_ready")),
        "headline_hit_rate": r.get("headline_hit_rate"),
        "promotion_recommendation": g.get("promotion_recommendation") or r.get("promotion_recommendation"),
        "outcome_class": g.get("outcome_class") or r.get("outcome_class"),
    }


def _run(py: str, step: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "step": step,
        "ok": cp.returncode == 0,
        "exit_code": cp.returncode,
        "tail": ((cp.stdout or "") + (cp.stderr or ""))[-800:],
    }


def _done(snap: dict[str, Any], *, target: str) -> bool:
    if target == "strict":
        return bool(snap.get("strict_passed"))
    if target == "combined":
        return bool(snap.get("combined_all_passed"))
    return bool(snap.get("strict_passed") or snap.get("combined_all_passed"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument(
        "--stop-on",
        choices=("combined", "strict", "either"),
        default="combined",
        help="Stop when this gate level passes (default: combined_all_passed).",
    )
    ap.add_argument(
        "--sweep-grid",
        default="2,2.5,3,3.5,4,5,6",
        help="neutral_bps grid for promotion_push and recommended eval sweeps.",
    )
    ap.add_argument("--skip-parallel", action="store_true")
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    baseline = _gate_snapshot()
    rounds: list[dict[str, Any]] = []

    for n in range(1, max(1, args.max_rounds) + 1):
        steps: list[dict[str, Any]] = []
        steps.append(
            _run(
                py,
                "promotion_push_180d",
                [
                    py,
                    "scripts/run_btrack_promotion_push_v1.py",
                    "--auto-sweep-grid",
                    args.sweep_grid,
                    "--recent-trading-days",
                    "180",
                ],
            )
        )
        steps.append(
            _run(
                py,
                "recommended_eval_30d_sweep",
                [
                    py,
                    "scripts/run_prophecy_btrack_recommended_eval_chain_v1.py",
                    "--auto-sweep-and-apply",
                    "--auto-sweep-grid",
                    args.sweep_grid,
                    "--recent-trading-days",
                    "30",
                ],
            )
        )
        if not args.skip_parallel:
            steps.append(
                _run(
                    py,
                    "parallel_10lane",
                    [py, "scripts/run_btrack_parallel_10lane_v1.py", "--max-workers", "6"],
                )
            )
        steps.append(
            _run(
                py,
                "restoration_spike",
                [py, "scripts/run_prophecy_restoration_spike.py"],
            )
        )
        steps.append(
            _run(
                py,
                "eval_gates_dual",
                [
                    py,
                    "scripts/eval_prophecy_promotion_gates_v1.py",
                    "--promotion-track-mode",
                    "dual",
                ],
            )
        )
        steps.append(_run(py, "readiness_report", [py, "scripts/build_prophecy_promotion_readiness_report_v1.py"]))
        steps.append(_run(py, "gate_evidence_pack", [py, "scripts/build_prophecy_gate_evidence_pack_v1.py"]))

        after = _gate_snapshot()
        rounds.append(
            {
                "round": n,
                "steps": steps,
                "snapshot_after": after,
                "round_ok": all(s.get("ok") for s in steps),
                "target_met": _done(after, target=args.stop_on),
            }
        )
        if _done(after, target=args.stop_on):
            break

    final = _gate_snapshot()
    doc = {
        "schema": "prophecy_improve_push_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "track_a_live_promotion": False,
        "stop_on": args.stop_on,
        "max_rounds": args.max_rounds,
        "sweep_grid": args.sweep_grid,
        "baseline": baseline,
        "final": final,
        "improved_vs_baseline": {
            "combined_all_passed": final.get("combined_all_passed") and not baseline.get("combined_all_passed"),
            "strict_passed": final.get("strict_passed") and not baseline.get("strict_passed"),
            "headline_hit_rate_delta": (
                (final.get("headline_hit_rate") or 0) - (baseline.get("headline_hit_rate") or 0)
                if final.get("headline_hit_rate") is not None and baseline.get("headline_hit_rate") is not None
                else None
            ),
        },
        "rounds": rounds,
        "target_met": _done(final, target=args.stop_on),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "target_met": doc["target_met"], "final": final, "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc["target_met"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
