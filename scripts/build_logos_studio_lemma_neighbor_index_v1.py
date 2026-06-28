#!/usr/bin/env python3
"""Build compact lemma↔verse index for Logos Studio lemma bridge v1.

Reproduce:
  py scripts/build_logos_studio_lemma_neighbor_index_v1.py
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.json"
DEFAULT_PKL = ROOT / "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.pkl"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_verse(raw: str) -> str:
    from scripts.logos_verse_ref_canonical_v1 import normalize_verse_ref

    return normalize_verse_ref(raw)


def build_index(edges_path: Path) -> dict[str, Any]:
    verse_to_lemmas: dict[str, set[str]] = defaultdict(set)
    lemma_to_verses: dict[str, set[str]] = defaultdict(set)
    edge_count = 0
    with edges_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            lemma = str(row.get("src_node_id") or "").strip()
            verse = _norm_verse(str(row.get("dst_node_id") or ""))
            if not lemma or not verse or "." not in verse:
                continue
            verse_to_lemmas[verse].add(lemma)
            lemma_to_verses[lemma].add(verse)
            edge_count += 1
    return {
        "schema": "logos_studio_lemma_neighbor_index_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "source_edges": str(edges_path.relative_to(ROOT)).replace("\\", "/"),
        "edge_count": edge_count,
        "verse_count": len(verse_to_lemmas),
        "lemma_count": len(lemma_to_verses),
        "verse_to_lemmas": {k: sorted(v) for k, v in verse_to_lemmas.items()},
        "lemma_to_verses": {k: sorted(v) for k, v in lemma_to_verses.items()},
        "reproduce": "py scripts/build_logos_studio_lemma_neighbor_index_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.edges.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {args.edges}"}), file=sys.stderr)
        return 2
    doc = build_index(args.edges)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pkl_path = DEFAULT_PKL if args.out.resolve() == DEFAULT_OUT.resolve() else args.out.with_suffix(".pkl")
    with pkl_path.open("wb") as fh:
        pickle.dump(
            {
                "schema": doc["schema"],
                "verse_to_lemmas": doc["verse_to_lemmas"],
                "lemma_to_verses": doc["lemma_to_verses"],
            },
            fh,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
                "pkl": str(pkl_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
                "verse_count": doc["verse_count"],
                "lemma_count": doc["lemma_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
