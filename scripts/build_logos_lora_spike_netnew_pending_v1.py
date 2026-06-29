#!/usr/bin/env python3
"""Build pending JSONL from LoRA spike survivors excluding canonical pairs ([HYPO] B-track)."""

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

from logos_candidate_edge_lane_common_v1 import undirected_pair_key

DEFAULT_SPIKE = ROOT / "docs/final/artifacts/logos_candidate_edge_survivors_lora_prune_spike_v1_latest.json"
DEFAULT_CANONICAL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_lora_netnew_v1.jsonl"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/logos_lora_spike_netnew_pending_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_pairs(path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if not path.is_file():
        return pairs
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if src and dst:
            pairs.add(undirected_pair_key(src, dst))
    return pairs


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def build_netnew_pending(
    spike_doc: dict[str, Any],
    canonical_path: Path,
    *,
    max_items: int = 18,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    canonical = _canonical_pairs(canonical_path)
    survivors = list(spike_doc.get("survivors") or [])
    survivors.sort(key=lambda r: -float(r.get("similarity_4d_cosine") or r.get("weight") or 0))

    selected: list[dict[str, Any]] = []
    skipped_duplicate = 0
    for row in survivors:
        if not isinstance(row, dict):
            continue
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if not src or not dst:
            continue
        key = undirected_pair_key(src, dst)
        if key in canonical:
            skipped_duplicate += 1
            continue
        selected.append(row)
        if len(selected) >= max(0, max_items):
            break

    report = {
        "schema": "logos_lora_spike_netnew_pending_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "max_items": max_items,
        "spike_survivor_count": int((spike_doc.get("stats") or {}).get("survivor_count") or len(survivors)),
        "netnew_selected": len(selected),
        "skipped_duplicate_vs_canonical": skipped_duplicate,
        "canonical_pair_count": len(canonical),
        "pending_jsonl": str(DEFAULT_OUT.relative_to(ROOT)).replace("\\", "/"),
    }
    return selected, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spike-survivors-json", type=Path, default=DEFAULT_SPIKE)
    ap.add_argument("--canonical-edges-jsonl", type=Path, default=DEFAULT_CANONICAL)
    ap.add_argument("--max-items", type=int, default=18)
    ap.add_argument("--pending-jsonl-out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    spike_path = args.spike_survivors_json if args.spike_survivors_json.is_absolute() else ROOT / args.spike_survivors_json
    canonical_path = (
        args.canonical_edges_jsonl if args.canonical_edges_jsonl.is_absolute() else ROOT / args.canonical_edges_jsonl
    )
    if not spike_path.is_file():
        print(f"Missing spike survivors: {spike_path}", file=sys.stderr)
        return 2

    spike_doc = _read_json(spike_path)
    selected, report = build_netnew_pending(spike_doc, canonical_path, max_items=int(args.max_items))
    report["pending_jsonl"] = str(
        (args.pending_jsonl_out if args.pending_jsonl_out.is_absolute() else ROOT / args.pending_jsonl_out)
        .relative_to(ROOT)
    ).replace("\\", "/")

    pending_path = args.pending_jsonl_out if args.pending_jsonl_out.is_absolute() else ROOT / args.pending_jsonl_out
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    with pending_path.open("w", encoding="utf-8") as fh:
        for row in selected:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    report_path = args.report_json if args.report_json.is_absolute() else ROOT / args.report_json
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "netnew_selected": len(selected), "report": str(report_path)}))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
