#!/usr/bin/env python3
"""Append full-corpus kNN spike pruned edges to meaning graph (W2 research batch).

  py scripts/ingest_logos_knn_spike_edges_w2_batch_v1.py
  py scripts/ingest_logos_knn_spike_edges_w2_batch_v1.py --pruned-jsonl path/to/pruned.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PRUNED = (
    ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_survivors_full_corpus_spike_v1.jsonl"
)
CANONICAL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
OUT_REPORT = ROOT / "reports/logos_knn_spike_w2_ingest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _existing_pairs(path: Path) -> set[tuple[str, str, str]]:
    pairs: set[tuple[str, str, str]] = set()
    if not path.is_file():
        return pairs
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        src = str(row.get("src_node_id") or row.get("src") or "")
        dst = str(row.get("dst_node_id") or row.get("dst") or "")
        et = str(row.get("edge_type") or "knn_candidate")
        if src and dst:
            pairs.add((src, dst, et))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pruned-jsonl", type=Path, default=DEFAULT_PRUNED)
    ap.add_argument("--out-jsonl", type=Path, default=CANONICAL)
    ap.add_argument("--max-edges", type=int, default=500)
    args = ap.parse_args()

    if not args.pruned_jsonl.is_file():
        report = {
            "schema": "logos_knn_spike_w2_ingest_v1",
            "ok": True,
            "skipped": True,
            "reason": "pruned_jsonl_missing",
            "path": str(args.pruned_jsonl),
        }
        OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    existing = _existing_pairs(args.out_jsonl)
    lines: list[str] = []
    added = 0
    for line in args.pruned_jsonl.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or added >= args.max_edges:
            break
        row = json.loads(line)
        if not isinstance(row, dict):
            continue
        src = str(row.get("src_node_id") or row.get("src") or "")
        dst = str(row.get("dst_node_id") or row.get("dst") or "")
        if not src or not dst:
            continue
        et = str(row.get("edge_type") or "knn_candidate_w2")
        key = (src, dst, et)
        if key in existing:
            continue
        existing.add(key)
        out_row: dict[str, Any] = {
            "schema": "logos_knn_spike_edge_w2_v1",
            "src_node_id": src,
            "dst_node_id": dst,
            "edge_type": et,
            "weight": float(row.get("weight") or row.get("cosine") or 0.4),
            "research_only": True,
            "hypothesis_tier": "B",
            "source": "full_corpus_knn_spike_w2",
        }
        lines.append(json.dumps(out_row, ensure_ascii=False))
        added += 1

    if lines:
        with args.out_jsonl.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    report = {
        "schema": "logos_knn_spike_w2_ingest_v1",
        "ok": True,
        "added_edges": added,
        "pruned_jsonl": str(args.pruned_jsonl),
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
