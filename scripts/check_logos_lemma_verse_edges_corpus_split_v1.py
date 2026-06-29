#!/usr/bin/env python3
"""Phase 1 gate: lemma-verse edge dst refs vs corpus manifest split ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/logos_lemma_verse_edges_corpus_split_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _corpus_verse_ids(corpus_path: Path) -> set[str]:
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Corpus must be a JSON array")
    out: set[str] = set()
    for row in data:
        if isinstance(row, dict):
            vid = row.get("verse_id")
            if isinstance(vid, str) and vid.strip():
                out.add(vid.strip())
    return out


def check(
    *,
    manifest_path: Path,
    edges_path: Path,
    min_edges: int,
    require_contain_in_corpus: bool,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rel_corpus = manifest.get("input_path")
    if not isinstance(rel_corpus, str):
        raise FileNotFoundError("manifest missing input_path")
    corpus_path = ROOT / rel_corpus.replace("/", "\\")
    if not corpus_path.is_file():
        raise FileNotFoundError(corpus_path)

    corpus_ids = _corpus_verse_ids(corpus_path)
    edges: list[dict[str, Any]] = []
    if edges_path.is_file():
        for line in edges_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                edges.append(row)

    by_type: dict[str, dict[str, int]] = {}
    not_in_sample: list[str] = []
    for row in edges:
        et = str(row.get("edge_type") or "UNKNOWN")
        dst = str(row.get("dst_node_id") or "").strip()
        bucket = by_type.setdefault(et, {"total": 0, "in_corpus": 0, "not_in_corpus": 0})
        bucket["total"] += 1
        if dst in corpus_ids:
            bucket["in_corpus"] += 1
        else:
            bucket["not_in_corpus"] += 1
            if len(not_in_sample) < 16:
                not_in_sample.append(dst)

    contain = by_type.get("CONTAIN", {"total": 0, "in_corpus": 0, "not_in_corpus": 0})
    total = len(edges)
    in_corpus_total = sum(b["in_corpus"] for b in by_type.values())

    gate_failures: list[str] = []
    if total < min_edges:
        gate_failures.append(f"edge_count {total} < min_edges {min_edges}")
    if require_contain_in_corpus and contain["not_in_corpus"] > 0:
        gate_failures.append(
            f"CONTAIN not_in_corpus={contain['not_in_corpus']} sample={not_in_sample[:8]}"
        )

    return {
        "schema": "logos_lemma_verse_edges_corpus_split_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "corpus_input_path": rel_corpus,
        "corpus_verse_count": len(corpus_ids),
        "edge_count": total,
        "edges_in_corpus_count": in_corpus_total,
        "edges_not_in_corpus_count": total - in_corpus_total,
        "by_edge_type": by_type,
        "not_in_corpus_sample": not_in_sample,
        "gate_pass": len(gate_failures) == 0,
        "gate_failures": gate_failures,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-edges", type=int, default=10)
    ap.add_argument(
        "--require-contain-in-corpus",
        action="store_true",
        default=True,
    )
    ap.add_argument(
        "--allow-contain-drift",
        action="store_false",
        dest="require_contain_in_corpus",
    )
    args = ap.parse_args()

    doc = check(
        manifest_path=args.manifest,
        edges_path=args.edges_jsonl,
        min_edges=args.min_edges,
        require_contain_in_corpus=args.require_contain_in_corpus,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["gate_pass"],
                "edge_count": doc["edge_count"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
