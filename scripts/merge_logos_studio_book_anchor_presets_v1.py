#!/usr/bin/env python3
"""Add 1 verse_anchor preset per canon book (66 OT+NT) — W3 router coverage.

  py scripts/merge_logos_studio_book_anchor_presets_v1.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.expand_logos_bible_full_corpus_batch_v1 import FULL_CANON_BOOK_ORDER  # noqa: E402
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
PIPELINE = ROOT / "data/logos/verse_4pipeline_full_31102.json"
OUT_REPORT = ROOT / "reports/logos_studio_book_anchor_presets_merge_v1_latest.json"
STUB_PREFIX = "showroom_router_stub_verse::"
BOOK_ANCHOR_PREFIX = "canon_book_anchor"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _first_verse_per_book() -> dict[str, str]:
    data = json.loads(PIPELINE.read_text(encoding="utf-8-sig"))
    out: dict[str, str] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        ref = canonical_verse_ref(str(row.get("verse_id") or ""))
        if not ref:
            continue
        book = ref.split(".", 1)[0]
        if book not in out:
            out[book] = ref
    return out


def _book_preset(
    book: str,
    first_ref: str,
    graph_doc: dict[str, Any],
) -> dict[str, Any]:
    anchor_id = f"{BOOK_ANCHOR_PREFIX}::{book}"
    highlights: list[str] = []
    for n in graph_doc.get("nodes") or []:
        nid = str(n.get("id") or "")
        if nid == anchor_id or str(n.get("ref") or "") == first_ref:
            highlights.append(nid)
    if not highlights:
        highlights = [f"{STUB_PREFIX}{canonical_verse_ref(first_ref)}"]
    refs = [first_ref]
    for n in graph_doc.get("nodes") or []:
        if str(n.get("ref") or "").startswith(f"{book}."):
            r = canonical_verse_ref(str(n.get("ref")))
            if r and r not in refs:
                refs.append(r)
            if len(refs) >= 6:
                break
    pid = f"book_{book.lower()}_anchor"
    return {
        "id": pid,
        "preset_kind": "verse_anchor",
        "book": book,
        "prompt_ko": f"{book} 권 앵커 · {first_ref}",
        "answer_ko": (
            f"[HYPO] **{book}** 권 그래프 앵커 프리셋 · {first_ref} · research_only · NON_GATING."
        ),
        "answer_ko_product": f"[HYPO] Book anchor {book} · {first_ref} · NON_GATING.",
        "highlight_node_ids": highlights[:48],
        "keywords": [book.lower(), book, f"{book} 권", "book anchor", first_ref],
        "router_path_v1": {
            "schema_version": "logos_router_path_v1",
            "verse_refs": refs[:6],
            "research_only": True,
            "send_gate": "HOLD",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    args = ap.parse_args()

    presets_doc = json.loads(args.presets_json.read_text(encoding="utf-8-sig"))
    graph_doc = json.loads(args.graph_json.read_text(encoding="utf-8-sig"))
    first_by_book = _first_verse_per_book()

    presets = list(presets_doc.get("presets") or [])
    by_id = {str(p.get("id")): i for i, p in enumerate(presets) if p.get("id")}
    added = 0
    books_touched: list[str] = []

    for book in FULL_CANON_BOOK_ORDER:
        first_ref = first_by_book.get(book)
        if not first_ref:
            continue
        row = _book_preset(book, first_ref, graph_doc)
        pid = row["id"]
        if pid in by_id:
            presets[by_id[pid]] = row
        else:
            presets.append(row)
            by_id[pid] = len(presets) - 1
            added += 1
        books_touched.append(book)

    presets_doc["presets"] = presets
    presets_doc["book_anchor_merge_v1"] = {
        "merged_at_utc": _utc(),
        "books": books_touched,
        "added": added,
        "research_only": True,
        "send_gate": "HOLD",
    }
    text = json.dumps(presets_doc, ensure_ascii=False, indent=2) + "\n"
    args.presets_json.write_text(text, encoding="utf-8")

    report = {
        "schema": "logos_studio_book_anchor_presets_merge_v1",
        "ok": True,
        "preset_count": len(presets),
        "books_merged": len(books_touched),
        "added": added,
        "reproduce": "py scripts/merge_logos_studio_book_anchor_presets_v1.py",
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
