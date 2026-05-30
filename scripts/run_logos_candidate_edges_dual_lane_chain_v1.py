#!/usr/bin/env python3
"""Dual-lane chain: 4D kNN + ANN-lite prune + cross-lane compare ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHAIN_4D = ROOT / "scripts/run_logos_candidate_edges_offline_knn_chain_v1.py"
CHAIN_ANN = ROOT / "scripts/run_logos_candidate_edges_ann_lite_chain_v1.py"
COMPARE = ROOT / "scripts/compare_logos_candidate_edge_lanes_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edges_dual_lane_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-build", action="store_true", help="Skip both candidate builds")
    ap.add_argument("--skip-4d", action="store_true")
    ap.add_argument("--skip-ann-lite", action="store_true")
    ap.add_argument("--skip-promotion-gate", action="store_true", help="4D chain only")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    if not args.skip_4d:
        cmd = [sys.executable, str(CHAIN_4D)]
        if args.skip_build:
            cmd.append("--skip-build")
        if args.skip_promotion_gate:
            cmd.append("--skip-promotion-gate")
        code, tail = _run(cmd)
        steps.append({"step": "chain_4d", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0 and not args.skip_ann_lite:
        cmd = [sys.executable, str(CHAIN_ANN)]
        if args.skip_build:
            cmd.append("--skip-build")
        code, tail = _run(cmd)
        steps.append({"step": "chain_ann_lite", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(COMPARE)])
        steps.append({"step": "lane_compare", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    doc = {
        "schema": "logos_candidate_edges_dual_lane_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "exit_code": exit_code,
        "steps": steps,
        "artifacts": {
            "compare_json": "docs/final/artifacts/logos_candidate_edge_lane_compare_v1_latest.json",
            "survivors_4d_json": "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json",
            "survivors_ann_lite_json": "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json",
        },
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
