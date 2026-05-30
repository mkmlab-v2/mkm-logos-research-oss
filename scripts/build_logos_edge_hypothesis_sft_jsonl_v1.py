#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build LoRA SFT JSONL from covenant-convergence review subset ([HYPO], human sign-off gate)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FILTERED = ROOT / "docs/final/artifacts/logos_review_queue_covenant_convergence_v1_latest.json"
DEFAULT_OUT_JSONL = ROOT / "docs/final/artifacts/logos_edge_hypothesis_sft_v1_latest.jsonl"
DEFAULT_OUT_MANIFEST = ROOT / "docs/final/artifacts/logos_edge_hypothesis_sft_manifest_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _instruction_for_edge(item: dict[str, Any], *, rank_emphasis: bool = False) -> str:
    src = item.get("src_node_id")
    dst = item.get("dst_node_id")
    edge_type = item.get("edge_type") or "semantic_ann_lite_knn"
    sim = item.get("similarity")
    rank = item.get("queue_rank")
    base = (
        "Logos meaning-graph edge hypothesis (B-track, research_only). "
        f"Propose a guarded semantic relation between nodes {src} and {dst}. "
        f"edge_type={edge_type}; ann_lite_similarity={sim}. "
        "Output must stay [HYPO], non_gating, and must not auto-merge to canonical."
    )
    if rank_emphasis and rank is not None:
        base += (
            f" CRITICAL: response MUST begin with the exact token queue_rank={rank} "
            f"and Candidate edge rank={rank} (do not substitute another rank)."
        )
    return base


def _output_for_edge(item: dict[str, Any], *, rank_emphasis: bool = False) -> str:
    src = item.get("src_node_id")
    dst = item.get("dst_node_id")
    sim = item.get("similarity")
    rank = item.get("queue_rank")
    rank_prefix = f"queue_rank={rank} | " if rank_emphasis and rank is not None else ""
    return (
        f"[HYPO] {rank_prefix}Candidate edge rank={rank}: {src} ↔ {dst} "
        f"(similarity={sim}). "
        "Relation basis: semantic_ann_lite_knn + covenant-convergence filter. "
        "NON_GATING · research_only · merge_to_canonical_allowed=false · "
        "awaiting human review_decision=approve before promotion."
    )


def build_sft_rows(
    filtered_doc: dict[str, Any],
    *,
    require_approved: bool = False,
    rank_emphasis: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in filtered_doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        if require_approved and item.get("review_decision") != "approve":
            continue
        rows.append(
            {
                "instruction": _instruction_for_edge(item, rank_emphasis=rank_emphasis),
                "input": "",
                "output": _output_for_edge(item, rank_emphasis=rank_emphasis),
                "metadata": {
                    "schema": "logos_edge_hypothesis_sft_v1",
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "non_gating": True,
                    "merge_to_canonical_allowed": False,
                    "queue_rank": item.get("queue_rank"),
                    "pair_key": item.get("pair_key"),
                    "lane_id": item.get("lane_id"),
                    "review_decision": item.get("review_decision"),
                },
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--filtered-json", type=Path, default=DEFAULT_FILTERED)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_OUT_MANIFEST)
    ap.add_argument(
        "--require-approved",
        action="store_true",
        help="Only rows with review_decision=approve (default: include pending for train-entry pack)",
    )
    ap.add_argument(
        "--rank-emphasis",
        action="store_true",
        help="Repeat queue_rank in instruction/output to reduce rank mode-collapse ([HYPO] experiment)",
    )
    args = ap.parse_args()

    filtered = _read_json(args.filtered_json)
    if not filtered.get("items"):
        print(json.dumps({"ok": False, "error": f"missing filtered items: {args.filtered_json}"}))
        return 1

    rows = build_sft_rows(
        filtered,
        require_approved=args.require_approved,
        rank_emphasis=args.rank_emphasis,
    )
    if not rows:
        print(json.dumps({"ok": False, "error": "no SFT rows after filter (require_approved?)"}))
        return 1

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    manifest = {
        "schema": "logos_edge_hypothesis_sft_manifest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "human_signoff_required": True,
        "require_approved": args.require_approved,
        "rank_emphasis": args.rank_emphasis,
        "row_count": len(rows),
        "jsonl_path": _rel(args.output_jsonl),
        "source_filtered": _rel(args.filtered_json),
        "train_entry_mode": "stub_pack_only",
    }
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "jsonl": str(args.output_jsonl), "manifest": str(args.manifest_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
