#!/usr/bin/env python3
"""Autonomous evolution loop draft — dry-run only; human gate required for commit.

Rails:
  - commander_hypothesis (default): P31d branch scores → proposal sketch only
  - compression: legacy snapshot from MULTILENS active report (no mutation)

Default: --dry-run --gate-profile minimal
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "autonomous_evolution_loop_draft_v1_latest.json"
SCORES_PATH = ROOT / "reports" / "commander_hypothesis_branch_scores_latest.json"
BASELINE_COMP = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_gate_minimal() -> Dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_commander_hypothesis_stream_v1.py",
        "tests/test_run_autonomous_evolution_loop_draft_v1.py",
        "-q",
        "--tb=line",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or "") + (proc.stderr or "")
    if len(tail) > 800:
        tail = ".." + tail[-800:]
    return {"exit_code": proc.returncode, "log_tail": tail}


def _step1_commander_snapshot(scores: Dict[str, Any]) -> Dict[str, Any]:
    summary = scores.get("summary") or {}
    return {
        "rail": "commander_hypothesis",
        "hypothesis_calendar_kst": scores.get("hypothesis_calendar_kst"),
        "market_direction": scores.get("market_direction"),
        "market_return_pct": scores.get("market_return_pct"),
        "branch_summary": summary,
        "n_branches_scored": summary.get("n_branches"),
    }


def _step2_proposal_commander(
    scores: Dict[str, Any],
    *,
    dry_run: bool,
) -> Dict[str, Any]:
    if dry_run:
        aligned = (scores.get("summary") or {}).get("aligned", 0)
        partial = (scores.get("summary") or {}).get("partial", 0)
        return {
            "status": "skipped_v1_dry_run",
            "note": (
                "Branch confidence weights are NOT auto-mutated. "
                f"Observed aligned={aligned} partial={partial}. "
                "Human may tune build_commander_hypothesis_stream_v1 rules after review."
            ),
            "would_consider": [
                "boost confidence on branches with repeated aligned outcomes",
                "demote branches with repeated partial+up conflicts",
            ],
        }
    return {"status": "forbidden_without_human_gate"}


def _step1_compression_snapshot() -> Dict[str, Any]:
    doc = _read_json(BASELINE_COMP)
    kpi = doc.get("active_kpi") or doc
    return {
        "rail": "compression",
        "global_token_saving_rate": kpi.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": kpi.get("avg_reconstruction_fidelity_jaccard"),
        "quality_gate": doc.get("quality_gate") or kpi.get("quality_gate"),
        "source_input": doc.get("source_input") or str(BASELINE_COMP),
    }


def run_loop(
    *,
    rail: str = "commander_hypothesis",
    dry_run: bool = True,
    max_rounds: int = 1,
    gate_profile: str = "minimal",
    scores_path: Path = SCORES_PATH,
) -> Dict[str, Any]:
    rounds: List[Dict[str, Any]] = []
    gate_result: Optional[Dict[str, Any]] = None
    gate_cmd = None

    for i in range(1, max_rounds + 1):
        if rail == "commander_hypothesis":
            scores = _read_json(scores_path)
            if not scores:
                step1 = {"error": f"missing_scores:{scores_path}"}
                step2 = {"status": "skipped_no_scores"}
            else:
                step1 = _step1_commander_snapshot(scores)
                step2 = _step2_proposal_commander(scores, dry_run=dry_run)
        else:
            step1 = _step1_compression_snapshot()
            step2 = {
                "status": "skipped_v1_dry_run",
                "note": "Theory constants / shard weights must not be mutated without explicit allowlist + human gate.",
            }

        step3 = {"exit_code": None, "log_tail": "gate_skipped"}
        step4 = "no_gate"
        if gate_profile == "minimal":
            gate_result = _run_gate_minimal()
            step3 = gate_result
            step4 = "gate_pass" if gate_result["exit_code"] == 0 else "gate_fail"
            gate_cmd = "pytest commander_hypothesis + evolution draft smoke"

        rounds.append(
            {
                "round_index": i,
                "step1_snapshot": step1,
                "step2_proposal": step2,
                "step3_validation": step3,
                "step4_decision": step4,
            }
        )

    return {
        "schema": "autonomous_evolution_loop_draft_v1",
        "ts_utc": _utc_now(),
        "dry_run": dry_run,
        "max_rounds": max_rounds,
        "rail": rail,
        "baseline_json": str(SCORES_PATH if rail == "commander_hypothesis" else BASELINE_COMP),
        "gate_profile": gate_profile,
        "gate_profile_resolved": gate_profile,
        "gate_cmd_effective": gate_cmd,
        "rounds": rounds,
        "risk_ack": [
            "No global optimum guarantee; guard against local overfit via held-out benches.",
            "Cap API spend; never unbounded optimize loops.",
            "Commander rail: no auto-edit of fortune telegram or Track A.",
            "Compression rail: do not auto-edit MKM_CORE_THEORY or quaternion constants in this draft.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rail", choices=("commander_hypothesis", "compression"), default="commander_hypothesis")
    ap.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Marks non-dry-run intent only; production mutation still forbidden in v1",
    )
    ap.add_argument("--max-rounds", type=int, default=1)
    ap.add_argument("--gate-profile", choices=("none", "minimal"), default="minimal")
    ap.add_argument("--scores-json", type=Path, default=SCORES_PATH)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    dry_run = not args.no_dry_run

    doc = run_loop(
        rail=args.rail,
        dry_run=dry_run,
        max_rounds=args.max_rounds,
        gate_profile=args.gate_profile,
        scores_path=args.scores_json,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    last = (doc.get("rounds") or [{}])[-1]
    print(f"decision={last.get('step4_decision')}")
    return 0 if last.get("step4_decision") in ("gate_pass", "no_gate") else 1


if __name__ == "__main__":
    raise SystemExit(main())
