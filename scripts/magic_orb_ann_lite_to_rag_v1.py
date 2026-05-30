#!/usr/bin/env python3
"""Convert logos_vector_ann_lite_query_result_v1 → magic_orb rag_evidence rows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def ann_query_doc_to_rag_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Build NON_GATING rag rows with logos_ann_lite: source_id prefix."""
    rows: list[dict[str, Any]] = []
    hits = doc.get("top_k") or doc.get("hits") or doc.get("results") or []
    if not isinstance(hits, list):
        return rows
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        vid = str(hit.get("verse_id") or hit.get("id") or "").strip()
        if not vid:
            continue
        score = hit.get("score") or hit.get("similarity") or hit.get("cosine")
        score_s = f"{float(score):.4f}" if score is not None else "n/a"
        rows.append(
            {
                "source_id": f"logos_ann_lite:verse:{vid}",
                "snippet": (
                    f"ANN-lite semantic hit verse_id={vid!r} score={score_s}\n"
                    f"embedding_mode={doc.get('embedding_mode') or 'unknown'}\n"
                    "---\n[HYPO ANN-lite retrieval; NON_GATING; research_only]"
                ),
                "match_score": float(score) if score is not None else 0.0,
                "lane": "ann_lite",
            }
        )
    return rows


def load_ann_rag_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        return []
    if doc.get("schema") == "logos_vector_ann_lite_query_result_v1":
        return ann_query_doc_to_rag_rows(doc)
    if doc.get("schema") == "magic_orb_ann_lite_rag_v1":
        rag = doc.get("rag_evidence") or []
        return [r for r in rag if isinstance(r, dict)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ann-query-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    args = ap.parse_args()
    qpath = args.ann_query_json if args.ann_query_json.is_absolute() else ROOT / args.ann_query_json
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    doc = json.loads(qpath.read_text(encoding="utf-8-sig"))
    rows = ann_query_doc_to_rag_rows(doc if isinstance(doc, dict) else {})
    payload = {
        "schema": "magic_orb_ann_lite_rag_v1",
        "rag_evidence": rows,
        "hit_count": len(rows),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hit_count": len(rows), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
