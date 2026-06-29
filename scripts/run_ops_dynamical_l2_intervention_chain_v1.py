#!/usr/bin/env python3
"""Ops dynamical L2 chain — before/after intervention snapshots [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    DEFAULT_JSONL,
    append_jsonl_row,
    build_report,
    eval_l2_interventions,
    read_jsonl,
    synthetic_bench_override,
    timeseries_row_from_bench,
    utc_now,
)

GOVERNED = ROOT / "scripts/run_reddit_agent_governed_v1.py"
OUT = ROOT / "reports/ops_dynamical_l2_intervention_chain_v1_latest.json"
L2_EVAL = ROOT / "reports/ops_dynamical_l2_eval_v1_latest.json"


def _run_cleanup() -> dict[str, Any]:
    cmd = [sys.executable, str(GOVERNED), "cleanup"]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    last = tail[-1] if tail else ""
    summary: dict[str, Any] | None = None
    try:
        summary = json.loads(last)
    except json.JSONDecodeError:
        summary = None
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "summary": summary,
        "tail": last,
    }


def run_chain(
    *,
    jsonl: Path,
    mode: str,
    skip_cleanup: bool,
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    steps: list[dict[str, Any]] = []

    if mode == "synthetic":
        before = synthetic_bench_override(stage="stress", stress_score=0.62)
        append_jsonl_row(
            jsonl,
            timeseries_row_from_bench(
                before,
                intervention={"applied": False, "kind": None, "session_id": session_id},
            ),
        )
        steps.append({"step": "synthetic_before", "stage": "stress", "stress": 0.62})
        after = synthetic_bench_override(stage="watch", stress_score=0.28)
        append_jsonl_row(
            jsonl,
            timeseries_row_from_bench(
                after,
                intervention={
                    "applied": True,
                    "kind": "reddit_cleanup_synthetic",
                    "ok": True,
                    "session_id": session_id,
                },
            ),
        )
        steps.append({"step": "synthetic_after", "stage": "watch", "stress": 0.28})
        cleanup_result = {"ok": True, "skipped": True, "mode": "synthetic"}
    else:
        before = build_report(fractal_level="L2_intervention")
        append_jsonl_row(
            jsonl,
            timeseries_row_from_bench(
                before,
                intervention={"applied": False, "kind": None, "session_id": session_id},
            ),
        )
        steps.append({"step": "live_before", "stage": before["state_machine"]["stage"]})

        if skip_cleanup:
            cleanup_result = {"ok": False, "skipped": True, "reason": "skip_cleanup_flag"}
        else:
            cleanup_result = _run_cleanup()
        steps.append({"step": "reddit_cleanup", **cleanup_result})

        after = build_report(fractal_level="L2_intervention")
        append_jsonl_row(
            jsonl,
            timeseries_row_from_bench(
                after,
                intervention={
                    "applied": True,
                    "kind": "reddit_cleanup",
                    "ok": bool(cleanup_result.get("ok")),
                    "session_id": session_id,
                },
            ),
        )
        steps.append({"step": "live_after", "stage": after["state_machine"]["stage"]})

    l2 = eval_l2_interventions(read_jsonl(jsonl))
    L2_EVAL.write_text(json.dumps(l2, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "schema": "ops_dynamical_l2_intervention_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fractal_level": "L2_intervention",
        "mode": mode,
        "session_id": session_id,
        "jsonl_path": str(jsonl).replace("\\", "/"),
        "steps": steps,
        "l2_eval_path": str(L2_EVAL).replace("\\", "/"),
        "l2_metrics": l2.get("metrics"),
        "ok": True,
        "reproduce": "py scripts/run_ops_dynamical_l2_intervention_chain_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ops dynamical L2 intervention chain")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--mode", choices=("live", "synthetic"), default="live")
    parser.add_argument("--skip-cleanup", action="store_true", help="live mode: skip CDP cleanup")
    args = parser.parse_args()

    doc = run_chain(jsonl=args.jsonl, mode=args.mode, skip_cleanup=args.skip_cleanup)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "mode": args.mode,
                "equilibrium_restore_rate": doc["l2_metrics"].get("equilibrium_restore_rate"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
