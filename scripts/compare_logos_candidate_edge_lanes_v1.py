#!/usr/bin/env python3
"""Compare 4D kNN vs ANN-lite survivor queues for LoRA/human review ([HYPO] B-track)."""
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

from logos_candidate_edge_lane_common_v1 import survivor_pair_keys, undirected_pair_key

DEFAULT_4D = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
DEFAULT_ANN = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_lane_compare_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_survivors_doc(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_lane_compare(
    doc_4d: dict[str, Any],
    doc_ann: dict[str, Any],
    *,
    max_review_samples: int = 20,
) -> dict[str, Any]:
    survivors_4d = list(doc_4d.get("survivors") or [])
    survivors_ann = list(doc_ann.get("survivors") or [])

    pairs_4d = survivor_pair_keys(survivors_4d)
    pairs_ann = survivor_pair_keys(survivors_ann)

    overlap = pairs_4d & pairs_ann
    only_4d = pairs_4d - pairs_ann
    only_ann = pairs_ann - pairs_4d

    def _sample_pairs(pairs: set[tuple[str, str]], limit: int) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for src, dst in sorted(pairs)[:limit]:
            out.append({"src_node_id": src, "dst_node_id": dst})
        return out

    recommendation = "ann_lite_primary"
    note_ko = (
        "4D 레인 포화·ANN-lite 분포 양호 — LoRA/휴먼 리뷰는 ANN-lite survivor 우선, "
        "4D overlap만 교차 확인 권장."
    )
    if len(pairs_ann) == 0 and len(pairs_4d) > 0:
        recommendation = "4d_only_fallback"
        note_ko = "ANN-lite survivor 없음 — 4D survivor만 리뷰 큐."
    elif len(overlap) >= max(1, min(len(pairs_4d), len(pairs_ann)) // 2):
        recommendation = "dual_review_overlap_high"
        note_ko = "양 레인 overlap 높음 — 교차 survivor를 LoRA prune 입력으로 묶어 검토."

    return {
        "schema": "logos_candidate_edge_lane_compare_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "lanes": {
            "offline_4d_knn": {
                "survivor_count": len(survivors_4d),
                "distinct_pairs": len(pairs_4d),
                "source_json": str(doc_4d.get("inputs", {}).get("edges_jsonl") or ""),
            },
            "ann_lite": {
                "survivor_count": len(survivors_ann),
                "distinct_pairs": len(pairs_ann),
                "source_json": str(doc_ann.get("inputs", {}).get("edges_jsonl") or ""),
            },
        },
        "pair_sets": {
            "overlap_count": len(overlap),
            "only_4d_count": len(only_4d),
            "only_ann_lite_count": len(only_ann),
            "union_count": len(pairs_4d | pairs_ann),
        },
        "review_queue_samples": {
            "overlap": _sample_pairs(overlap, max_review_samples),
            "only_4d": _sample_pairs(only_4d, max_review_samples),
            "only_ann_lite": _sample_pairs(only_ann, max_review_samples),
        },
        "recommendation": recommendation,
        "recommendation_note_ko": note_ko,
        "next_steps_ko": [
            "signoff JSON approved=true + saturation_warning_acknowledged (4D lane only)",
            "check_logos_candidate_edge_promotion_gate_v1.py --strict (per lane survivor path)",
            "promote_logos_candidate_edge_survivors_v1.py → pending jsonl (canonical merge 별도 플래그)",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--survivors-4d-json", type=Path, default=DEFAULT_4D)
    ap.add_argument("--survivors-ann-json", type=Path, default=DEFAULT_ANN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-review-samples", type=int, default=20)
    args = ap.parse_args()

    path_4d = args.survivors_4d_json if args.survivors_4d_json.is_absolute() else ROOT / args.survivors_4d_json
    path_ann = args.survivors_ann_json if args.survivors_ann_json.is_absolute() else ROOT / args.survivors_ann_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    missing = [p for p in (path_4d, path_ann) if not p.is_file()]
    if missing:
        for p in missing:
            print(f"Missing survivor json: {p}", file=sys.stderr)
        return 2

    doc = build_lane_compare(
        _load_survivors_doc(path_4d),
        _load_survivors_doc(path_ann),
        max_review_samples=max(1, int(args.max_review_samples)),
    )
    doc["inputs"] = {
        "survivors_4d_json": str(path_4d.resolve()).replace("\\", "/"),
        "survivors_ann_json": str(path_ann.resolve()).replace("\\", "/"),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
