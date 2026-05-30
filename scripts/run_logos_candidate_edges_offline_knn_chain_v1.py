#!/usr/bin/env python3
"""Chain: offline 4D kNN candidate build -> quality report -> survivor prune ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILD = ROOT / "scripts/build_logos_candidate_edges_offline_knn_v1.py"
REPORT = ROOT / "scripts/report_logos_candidate_edges_quality_v1.py"
SELECT = ROOT / "scripts/select_logos_candidate_edge_survivors_v1.py"
GATE = ROOT / "scripts/check_logos_candidate_edge_promotion_gate_v1.py"
DEFAULT_CHAIN_OUT = ROOT / "docs/final/artifacts/logos_candidate_edges_offline_knn_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    combined = out if out else err
    return int(proc.returncode), combined


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--max-verses", type=int, default=2000)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--min-cosine", type=float, default=0.92)
    ap.add_argument("--max-candidates", type=int, default=5000)
    ap.add_argument("--survivor-top-n", type=int, default=200)
    ap.add_argument("--survivor-max-cosine", type=float, default=0.998)
    ap.add_argument("--skip-promotion-gate", action="store_true")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    if not args.skip_build:
        code, tail = _run(
            [
                sys.executable,
                str(BUILD),
                "--max-verses",
                str(int(args.max_verses)),
                "--top-k",
                str(int(args.top_k)),
                "--min-cosine",
                str(float(args.min_cosine)),
                "--max-candidates",
                str(int(args.max_candidates)),
            ]
        )
        steps.append({"step": "build_candidates", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run([sys.executable, str(REPORT)])
        steps.append({"step": "quality_report", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run(
            [
                sys.executable,
                str(SELECT),
                "--top-n",
                str(int(args.survivor_top_n)),
                "--max-cosine",
                str(float(args.survivor_max_cosine)),
                "--min-cosine",
                str(float(args.min_cosine)),
            ]
        )
        steps.append({"step": "select_survivors", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0 and not args.skip_promotion_gate:
        code, tail = _run([sys.executable, str(GATE)])
        steps.append({"step": "promotion_gate", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    chain_doc = {
        "schema": "logos_candidate_edges_offline_knn_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "exit_code": exit_code,
        "steps": steps,
        "artifacts": {
            "candidates_jsonl": "docs/final/artifacts/bible_meaning_graph_edges_candidate_v1.jsonl",
            "quality_json": "docs/final/artifacts/logos_candidate_edges_quality_v1_latest.json",
            "survivors_json": "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json",
            "survivors_pruned_jsonl": "docs/final/artifacts/bible_meaning_graph_edges_candidate_survivors_v1.jsonl",
            "promotion_gate_json": "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json",
        },
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
