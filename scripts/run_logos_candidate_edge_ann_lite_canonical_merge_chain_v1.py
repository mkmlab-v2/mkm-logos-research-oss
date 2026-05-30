#!/usr/bin/env python3
"""Merge ANN-lite pending batch → canonical + gold/subgraph verify ([HYPO] B-track).

Small batch only (default ann_lite pending ~45). Does not touch offline_4d bulk.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MERGE = ROOT / "scripts/apply_logos_approved_pending_to_canonical_v1.py"
GOLD = ROOT / "scripts/build_logos_gold_query_eval_report_v1.py"
SUBGRAPH = ROOT / "scripts/Invoke-GraphSubgraphLaneRecommendedChain_v1.ps1"
ANN_LITE_PENDING = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_ann_lite_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_ann_lite_canonical_merge_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return int(proc.returncode), out if out else err


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-canonical-merge", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    ap.add_argument("--pending-jsonl", type=Path, default=ANN_LITE_PENDING)
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pending = args.pending_jsonl if args.pending_jsonl.is_absolute() else ROOT / args.pending_jsonl
    if not pending.is_file():
        print(f"Missing pending JSONL: {pending}", file=sys.stderr)
        return 2

    steps: list[dict] = []
    exit_code = 0
    merge_report: dict = {}

    if not args.skip_canonical_merge:
        code, tail = _run(
            [
                sys.executable,
                str(MERGE),
                "--acknowledge-canonical-risk",
                "--refresh-bundle",
                "--pending-jsonl",
                str(pending),
            ]
        )
        steps.append({"step": "canonical_merge_ann_lite", "exit_code": code, "tail": tail})
        merge_path = ROOT / "docs/final/artifacts/logos_candidate_edge_canonical_merge_v1_latest.json"
        if merge_path.is_file():
            try:
                merge_report = json.loads(merge_path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                merge_report = {}
        if code != 0:
            exit_code = code

    if exit_code == 0 and not args.skip_verify:
        code, tail = _run([sys.executable, str(GOLD)])
        steps.append({"step": "gold_query_eval", "exit_code": code, "tail": tail[-400:] if len(tail) > 400 else tail})
        if code != 0:
            exit_code = code

    if exit_code == 0 and not args.skip_verify:
        code, tail = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SUBGRAPH),
                "-SkipPetPoC",
                "-SkipDeviceGraphSync",
            ]
        )
        steps.append(
            {
                "step": "subgraph_replay",
                "exit_code": code,
                "tail": tail[-500:] if len(tail) > 500 else tail,
            }
        )
        if code != 0:
            exit_code = code

    doc = {
        "schema": "logos_candidate_edge_ann_lite_canonical_merge_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "lane_id": "ann_lite",
        "batch_label": "ann_lite_primary_45",
        "canonical_merge_ran": not args.skip_canonical_merge,
        "exit_code": exit_code,
        "merge_summary": {
            "appended_count": merge_report.get("appended_count"),
            "skipped_duplicate": merge_report.get("skipped_duplicate"),
            "canonical_pairs_before": merge_report.get("canonical_pairs_before"),
            "canonical_pairs_after": merge_report.get("canonical_pairs_after"),
            "appended_by_lane": merge_report.get("appended_by_lane"),
        },
        "steps": steps,
        "artifacts": {
            "pending_jsonl": str(pending.relative_to(ROOT)).replace("\\", "/"),
            "merge_report": "docs/final/artifacts/logos_candidate_edge_canonical_merge_v1_latest.json",
            "bundle_json": "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
            "gold_eval_json": "reports/logos_gold_query_eval_v1_latest.json",
        },
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
