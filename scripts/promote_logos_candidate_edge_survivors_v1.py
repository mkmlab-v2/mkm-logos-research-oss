#!/usr/bin/env python3
"""Promote approved survivor edges to pending JSONL ([HYPO] B-track).

Requires promotion gate PASS. Never writes to canonical edges unless --apply-to-canonical
AND gate PASS AND --acknowledge-canonical-risk (human-only triple guard).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json"
DEFAULT_SURVIVORS = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json"
DEFAULT_QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
DEFAULT_PENDING = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_v1.jsonl"
DEFAULT_CANONICAL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_v1_latest.json"

LANE_PENDING: dict[str, str] = {
    "offline_4d_knn": "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_v1.jsonl",
    "ann_lite": "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_ann_lite_v1.jsonl",
}

LANE_GATE: dict[str, str] = {
    "offline_4d_knn": "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json",
    "ann_lite": "docs/final/artifacts/logos_candidate_edge_promotion_gate_ann_lite_v1_latest.json",
}

LANE_SURVIVORS: dict[str, str] = {
    "offline_4d_knn": "docs/final/artifacts/logos_candidate_edge_survivors_v1_latest.json",
    "ann_lite": "docs/final/artifacts/logos_candidate_edge_survivors_ann_lite_v1_latest.json",
}

LANE_PROMO_OUT: dict[str, str] = {
    "offline_4d_knn": "docs/final/artifacts/logos_candidate_edge_promotion_v1_latest.json",
    "ann_lite": "docs/final/artifacts/logos_candidate_edge_promotion_ann_lite_v1_latest.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _survivor_pair_key_str(row: dict[str, Any]) -> str:
    from logos_candidate_edge_lane_common_v1 import undirected_pair_key

    src = str(row.get("src_node_id") or "")
    dst = str(row.get("dst_node_id") or "")
    a, b = undirected_pair_key(src, dst)
    return f"{a}|{b}"


def _queue_pair_keys_for_decision(queue_doc: dict[str, Any], decision: str) -> set[str]:
    keys: set[str] = set()
    for item in queue_doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("review_decision") or "") != decision:
            continue
        pk = str(item.get("pair_key") or "").strip()
        if pk:
            keys.add(pk)
    return keys


def _filter_survivors_by_queue(
    survivors: list[dict[str, Any]],
    queue_doc: dict[str, Any],
    *,
    decision: str,
) -> list[dict[str, Any]]:
    allowed = _queue_pair_keys_for_decision(queue_doc, decision)
    if not allowed:
        return []
    out: list[dict[str, Any]] = []
    for row in survivors:
        if _survivor_pair_key_str(row) in allowed:
            out.append(row)
    return out


def _to_canonical_row(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "bible_meaning_graph_edge_v1",
        "src_node_id": candidate["src_node_id"],
        "dst_node_id": candidate["dst_node_id"],
        "edge_type": "theme_association",
        "weight": round(float(candidate.get("weight", 0.5)), 6),
        "source": "logos_candidate_edge_promotion_v1",
        "promoted_from": candidate.get("schema"),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane-id", choices=sorted(LANE_PENDING.keys()), default="offline_4d_knn")
    ap.add_argument("--gate-json", type=Path, default=None)
    ap.add_argument("--survivors-json", type=Path, default=None)
    ap.add_argument("--pending-jsonl-out", type=Path, default=None)
    ap.add_argument("--canonical-edges-jsonl", type=Path, default=DEFAULT_CANONICAL)
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument(
        "--queue-json",
        type=Path,
        default=None,
        help="When set, promote only survivors whose pair matches queue review_decision",
    )
    ap.add_argument(
        "--queue-filter-decision",
        default="approve",
        help="Queue review_decision filter (default approve)",
    )
    ap.add_argument("--apply-to-canonical", action="store_true")
    ap.add_argument("--acknowledge-canonical-risk", action="store_true")
    args = ap.parse_args()

    lane = str(args.lane_id)
    gate_path = Path(args.gate_json) if args.gate_json else ROOT / LANE_GATE[lane]
    surv_path = Path(args.survivors_json) if args.survivors_json else ROOT / LANE_SURVIVORS[lane]
    pending_path = Path(args.pending_jsonl_out) if args.pending_jsonl_out else ROOT / LANE_PENDING[lane]
    out_path = Path(args.output_json) if args.output_json else ROOT / LANE_PROMO_OUT[lane]
    canonical_path = (
        args.canonical_edges_jsonl if args.canonical_edges_jsonl.is_absolute() else ROOT / args.canonical_edges_jsonl
    )

    gate_path = gate_path if gate_path.is_absolute() else ROOT / gate_path
    surv_path = surv_path if surv_path.is_absolute() else ROOT / surv_path
    pending_path = pending_path if pending_path.is_absolute() else ROOT / pending_path
    out_path = out_path if out_path.is_absolute() else ROOT / out_path

    gate = _read_json(gate_path)
    survivors_doc = _read_json(surv_path)

    if not gate.get("gate_pass"):
        print("promotion gate HOLD — run check_logos_candidate_edge_promotion_gate_v1.py", file=sys.stderr)
        return 2

    survivors = list(survivors_doc.get("survivors") or [])
    queue_path: Path | None = None
    if args.queue_json:
        queue_path = args.queue_json if args.queue_json.is_absolute() else ROOT / args.queue_json
        queue_doc = _read_json(queue_path)
        survivors = _filter_survivors_by_queue(
            survivors, queue_doc, decision=str(args.queue_filter_decision)
        )
    if not survivors:
        print("no survivors to promote", file=sys.stderr)
        return 2

    pending_path.parent.mkdir(parents=True, exist_ok=True)
    with pending_path.open("w", encoding="utf-8") as fh:
        for row in survivors:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    canonical_appended = 0
    if args.apply_to_canonical:
        if not args.acknowledge_canonical_risk:
            print("refused: --apply-to-canonical requires --acknowledge-canonical-risk", file=sys.stderr)
            return 3
        canonical_rows = [_to_canonical_row(s) for s in survivors]
        with canonical_path.open("a", encoding="utf-8") as fh:
            for row in canonical_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        canonical_appended = len(canonical_rows)

    report = {
        "schema": "logos_candidate_edge_promotion_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "lane_id": lane,
        "status": "PROMOTED_TO_PENDING" if canonical_appended == 0 else "PROMOTED_TO_CANONICAL_APPEND",
        "promoted_count": len(survivors),
        "queue_filter": (
            {
                "queue_json": str(queue_path.resolve()).replace("\\", "/"),
                "review_decision": str(args.queue_filter_decision),
            }
            if queue_path
            else None
        ),
        "canonical_appended": canonical_appended,
        "pending_jsonl": str(pending_path.resolve()).replace("\\", "/"),
        "gate_json": str(gate_path.resolve()).replace("\\", "/"),
        "disclaimer_ko": "pending JSONL만 기본. canonical append는 명시 플래그 2개 필요.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
