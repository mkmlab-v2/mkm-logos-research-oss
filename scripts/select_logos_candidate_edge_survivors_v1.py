#!/usr/bin/env python3
"""Prune staging candidate edges to a survivor review queue ([HYPO] B-track).

Does not merge into bible_meaning_graph_edges_v1.jsonl — promotion gate + LoRA/human later.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
DEFAULT_PRUNED = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_survivors_v1.jsonl"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from logos_candidate_edge_lane_common_v1 import edge_lane_id, edge_similarity


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_edges(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def select_survivors(
    edges: list[dict[str, Any]],
    *,
    top_n: int,
    max_per_src: int,
    min_cosine: float,
    max_cosine: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    rejected: dict[str, int] = {
        "below_min_cosine": 0,
        "above_max_cosine": 0,
        "wrong_schema": 0,
    }

    for e in edges:
        if e.get("schema") != "bible_meaning_graph_edge_candidate_v1":
            rejected["wrong_schema"] += 1
            continue
        sim = edge_similarity(e)
        if sim < min_cosine:
            rejected["below_min_cosine"] += 1
            continue
        if sim > max_cosine:
            rejected["above_max_cosine"] += 1
            continue
        filtered.append(e)

    filtered.sort(key=lambda r: edge_similarity(r), reverse=True)

    src_counts: dict[str, int] = {}
    survivors: list[dict[str, Any]] = []
    for e in filtered:
        src = str(e.get("src_node_id") or "")
        if not src:
            continue
        if src_counts.get(src, 0) >= max_per_src:
            continue
        src_counts[src] = src_counts.get(src, 0) + 1
        survivors.append(e)
        if len(survivors) >= top_n:
            break

    stats = {
        "input_edge_count": len(edges),
        "filtered_edge_count": len(filtered),
        "survivor_count": len(survivors),
        "rejected": rejected,
        "top_n_cap": top_n,
        "max_per_src": max_per_src,
        "min_cosine": min_cosine,
        "max_cosine": max_cosine,
    }
    return survivors, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--pruned-jsonl-out",
        type=Path,
        default=DEFAULT_PRUNED,
        help="Optional JSONL of survivor rows for human/LoRA review",
    )
    ap.add_argument("--top-n", type=int, default=200)
    ap.add_argument("--max-per-src", type=int, default=1)
    ap.add_argument("--min-cosine", type=float, default=0.92)
    ap.add_argument(
        "--max-cosine",
        type=float,
        default=0.998,
        help="Drop near-duplicate matches (default 0.998 for 4D; use ~0.995 for ann_lite)",
    )
    ap.add_argument("--lane-id", type=str, default=None)
    ap.add_argument("--skip-pruned-jsonl", action="store_true")
    args = ap.parse_args()

    if args.top_n < 1:
        print("--top-n must be >= 1", file=sys.stderr)
        return 2

    edges_path = args.edges_jsonl if args.edges_jsonl.is_absolute() else ROOT / args.edges_jsonl
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    pruned_path = (
        args.pruned_jsonl_out if args.pruned_jsonl_out.is_absolute() else ROOT / args.pruned_jsonl_out
    )

    if not edges_path.is_file():
        print(f"Missing edges jsonl: {edges_path}", file=sys.stderr)
        return 2

    edges = _load_edges(edges_path)
    survivors, stats = select_survivors(
        edges,
        top_n=int(args.top_n),
        max_per_src=max(1, int(args.max_per_src)),
        min_cosine=float(args.min_cosine),
        max_cosine=float(args.max_cosine),
    )

    lane = args.lane_id or (edge_lane_id(edges[0]) if edges else "unknown")

    doc = {
        "schema": "logos_candidate_edge_survivors_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "hypothesis_tier": "B",
        "lane_id": lane,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "disclaimer_ko": "LoRA/휴먼 sign-off 전 canonical graph merge 금지.",
        "stats": stats,
        "survivors": survivors,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_pruned_jsonl and survivors:
        pruned_path.parent.mkdir(parents=True, exist_ok=True)
        with pruned_path.open("w", encoding="utf-8") as fh:
            for row in survivors:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(str(out_path))
    if not args.skip_pruned_jsonl and survivors:
        print(str(pruned_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
