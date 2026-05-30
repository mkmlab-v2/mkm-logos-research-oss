#!/usr/bin/env python3
"""Aggregate quality stats for bible_meaning_graph_edges_candidate_v1.jsonl ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edges_quality_v1_latest.json"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from logos_candidate_edge_lane_common_v1 import edge_lane_id, edge_similarity


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_edges(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def build_quality_report(edges: list[dict[str, Any]], *, lane_id: str | None = None) -> dict[str, Any]:
    lane = lane_id or (edge_lane_id(edges[0]) if edges else "unknown")
    sims = [edge_similarity(e) for e in edges]
    n = max(1, len(sims))
    mean_sim = sum(sims) / n if sims else 0.0
    min_sim = min(sims) if sims else 0.0
    max_sim = max(sims) if sims else 0.0

    buckets = {
        "ge_0_999": sum(1 for s in sims if s >= 0.999),
        "0_995_0_999": sum(1 for s in sims if 0.995 <= s < 0.999),
        "0_98_0_995": sum(1 for s in sims if 0.98 <= s < 0.995),
        "lt_0_98": sum(1 for s in sims if s < 0.98),
    }

    src_counts: dict[str, int] = {}
    for e in edges:
        src = str(e.get("src_node_id") or "")
        if src:
            src_counts[src] = src_counts.get(src, 0) + 1

    saturation_warning = lane == "offline_4d_knn" and (
        mean_sim >= 0.995 or buckets["ge_0_999"] >= max(1, len(sims) // 2)
    )

    sim_label = "similarity_ann_lite_cosine" if lane == "ann_lite" else "similarity_4d_cosine"

    return {
        "schema": "logos_candidate_edges_quality_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "hypothesis_tier": "B",
        "lane_id": lane,
        "similarity_field": sim_label,
        "edge_count": len(edges),
        "similarity_mean": round(mean_sim, 6),
        "similarity_min": round(min_sim, 6),
        "similarity_max": round(max_sim, 6),
        "similarity_4d_cosine_mean": round(mean_sim, 6),
        "similarity_4d_cosine_min": round(min_sim, 6),
        "similarity_4d_cosine_max": round(max_sim, 6),
        "similarity_histogram": buckets,
        "distinct_src_nodes": len(src_counts),
        "max_edges_per_src": max(src_counts.values()) if src_counts else 0,
        "saturation_warning": saturation_warning,
        "saturation_note_ko": (
            "4D cosine가 0.999+에 몰리면 pipeline1_simple_4d 벡터 포화 가능 — survivor max_cosine·LoRA prune 권장."
            if saturation_warning
            else (
                "ANN-lite/ST 레인 — 포화 경고 비활성(4D 전용)."
                if lane == "ann_lite"
                else "유사도 분포가 극단 포화 구간은 아님."
            )
        ),
        "gate_hints": {
            "recommended_max_cosine_for_survivor": 0.998 if lane == "offline_4d_knn" else 0.995,
            "recommended_max_per_src": 1,
            "lora_prune_pending": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--lane-id", type=str, default=None, help="offline_4d_knn | ann_lite (auto-detect if omitted)")
    args = ap.parse_args()

    edges_path = args.edges_jsonl if args.edges_jsonl.is_absolute() else ROOT / args.edges_jsonl
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not edges_path.is_file():
        print(f"Missing edges jsonl: {edges_path}", file=sys.stderr)
        return 2

    edges = _load_edges(edges_path)
    doc = build_quality_report(edges, lane_id=args.lane_id)
    doc["inputs"] = {"edges_jsonl": str(edges_path.resolve()).replace("\\", "/")}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
