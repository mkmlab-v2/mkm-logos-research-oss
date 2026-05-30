#!/usr/bin/env python3
"""Chain: ANN-lite candidate build -> quality -> survivor prune ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILD = ROOT / "scripts/build_logos_candidate_edges_from_ann_lite_v1.py"
REPORT = ROOT / "scripts/report_logos_candidate_edges_quality_v1.py"
SELECT = ROOT / "scripts/select_logos_candidate_edge_survivors_v1.py"
DEFAULT_CHAIN_OUT = ROOT / "docs/final/artifacts/logos_candidate_edges_ann_lite_chain_v1_latest.json"

CANDIDATES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_ann_lite_v1.jsonl"
QUALITY = ROOT / "docs/final/artifacts/logos_candidate_edges_quality_ann_lite_v1_latest.json"
SURVIVORS = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json"
PRUNED = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_survivors_ann_lite_v1.jsonl"


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
    ap.add_argument("--max-query-verses", type=int, default=500)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--min-cosine", type=float, default=0.78)
    ap.add_argument("--max-candidates", type=int, default=5000)
    ap.add_argument("--survivor-top-n", type=int, default=200)
    ap.add_argument("--survivor-max-cosine", type=float, default=0.995)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    exit_code = 0

    if not args.skip_build:
        code, tail = _run(
            [
                sys.executable,
                str(BUILD),
                "--max-query-verses",
                str(int(args.max_query_verses)),
                "--top-k",
                str(int(args.top_k)),
                "--min-cosine",
                str(float(args.min_cosine)),
                "--max-candidates",
                str(int(args.max_candidates)),
            ]
        )
        steps.append({"step": "build_ann_lite_candidates", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run(
            [
                sys.executable,
                str(REPORT),
                "--edges-jsonl",
                str(CANDIDATES),
                "--output-json",
                str(QUALITY),
                "--lane-id",
                "ann_lite",
            ]
        )
        steps.append({"step": "quality_report", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    if exit_code == 0:
        code, tail = _run(
            [
                sys.executable,
                str(SELECT),
                "--edges-jsonl",
                str(CANDIDATES),
                "--output-json",
                str(SURVIVORS),
                "--pruned-jsonl-out",
                str(PRUNED),
                "--top-n",
                str(int(args.survivor_top_n)),
                "--max-cosine",
                str(float(args.survivor_max_cosine)),
                "--min-cosine",
                str(float(args.min_cosine)),
                "--lane-id",
                "ann_lite",
            ]
        )
        steps.append({"step": "select_survivors", "exit_code": code, "tail": tail})
        if code != 0:
            exit_code = code

    chain_doc = {
        "schema": "logos_candidate_edges_ann_lite_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "lane_id": "ann_lite",
        "exit_code": exit_code,
        "steps": steps,
        "artifacts": {
            "candidates_jsonl": str(CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
            "quality_json": str(QUALITY.relative_to(ROOT)).replace("\\", "/"),
            "survivors_json": str(SURVIVORS.relative_to(ROOT)).replace("\\", "/"),
            "survivors_pruned_jsonl": str(PRUNED.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
