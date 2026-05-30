#!/usr/bin/env python3
"""Assemble LoRA/human review queue from dual-lane survivors + compare ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from logos_candidate_edge_lane_common_v1 import edge_similarity, undirected_pair_key

DEFAULT_SURV_4D = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
DEFAULT_SURV_ANN = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json"
DEFAULT_COMPARE = ROOT / "docs/final/artifacts/logos_candidate_edge_lane_compare_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _pair_index(survivors: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in survivors:
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if not src or not dst:
            continue
        out[undirected_pair_key(src, dst)] = row
    return out


def build_review_queue(
    survivors_4d_doc: dict[str, Any],
    survivors_ann_doc: dict[str, Any],
    compare_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ann_rows = list(survivors_ann_doc.get("survivors") or [])
    d4_rows = list(survivors_4d_doc.get("survivors") or [])
    ann_index = _pair_index(ann_rows)
    d4_index = _pair_index(d4_rows)

    overlap_keys = set(ann_index) & set(d4_index)
    only_ann = set(ann_index) - overlap_keys
    only_4d = set(d4_index) - overlap_keys

    items: list[dict[str, Any]] = []
    rank = 0

    def _append(pair: tuple[str, str], lane: str, priority: str, row: dict[str, Any]) -> None:
        nonlocal rank
        rank += 1
        items.append(
            {
                "queue_rank": rank,
                "lane_id": lane,
                "priority": priority,
                "pair_key": f"{pair[0]}|{pair[1]}",
                "src_node_id": row.get("src_node_id"),
                "dst_node_id": row.get("dst_node_id"),
                "edge_type": row.get("edge_type"),
                "similarity": round(edge_similarity(row), 6),
                "review_status": "pending",
                "review_decision": None,
                "review_notes_ko": None,
            }
        )

    for key in sorted(only_ann, key=lambda k: (-edge_similarity(ann_index[k]), k[0], k[1])):
        _append(key, "ann_lite", "primary", ann_index[key])

    for key in sorted(overlap_keys, key=lambda k: (-edge_similarity(ann_index[k]), k[0], k[1])):
        _append(key, "ann_lite", "overlap_dual_lane", ann_index[key])

    for key in sorted(only_4d, key=lambda k: (-edge_similarity(d4_index[k]), k[0], k[1])):
        _append(key, "offline_4d_knn", "secondary_4d_only", d4_index[key])

    recommendation = (compare_doc or {}).get("recommendation") or "ann_lite_primary"

    return {
        "schema": "logos_candidate_edge_human_review_queue_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "recommendation": recommendation,
        "stats": {
            "total_items": len(items),
            "ann_lite_primary": len(only_ann),
            "overlap_dual_lane": len(overlap_keys),
            "offline_4d_only": len(only_4d),
            "pending_count": len(items),
            "approved_count": 0,
            "rejected_count": 0,
        },
        "review_instructions_ko": [
            "각 item review_decision: approve | reject | defer",
            "ANN-lite primary(45) 먼저 — 4D-only는 포화 레인 보조",
            "승인 후 lane별 signoff JSON approved=true → promotion gate → pending jsonl",
        ],
        "items": items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--survivors-4d-json", type=Path, default=DEFAULT_SURV_4D)
    ap.add_argument("--survivors-ann-json", type=Path, default=DEFAULT_SURV_ANN)
    ap.add_argument("--compare-json", type=Path, default=DEFAULT_COMPARE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    path_4d = args.survivors_4d_json if args.survivors_4d_json.is_absolute() else ROOT / args.survivors_4d_json
    path_ann = args.survivors_ann_json if args.survivors_ann_json.is_absolute() else ROOT / args.survivors_ann_json
    path_cmp = args.compare_json if args.compare_json.is_absolute() else ROOT / args.compare_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    missing = [p for p in (path_4d, path_ann) if not p.is_file()]
    if missing:
        for p in missing:
            print(f"Missing survivor json: {p}", file=sys.stderr)
        return 2

    doc = build_review_queue(
        _read_json(path_4d),
        _read_json(path_ann),
        _read_json(path_cmp) if path_cmp.is_file() else None,
    )
    doc["inputs"] = {
        "survivors_4d_json": str(path_4d.resolve()).replace("\\", "/"),
        "survivors_ann_json": str(path_ann.resolve()).replace("\\", "/"),
        "compare_json": str(path_cmp.resolve()).replace("\\", "/") if path_cmp.is_file() else None,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
