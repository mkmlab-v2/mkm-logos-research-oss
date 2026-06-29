#!/usr/bin/env python3
"""Merge themed vector query hits into distill JSON provenance (deterministic)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge_vector_query(distill: dict[str, Any], query_doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(distill)
    top_k = query_doc.get("top_k") or []
    hits = []
    for row in top_k:
        if isinstance(row, dict) and row.get("verse_id"):
            hits.append({"verse_id": row["verse_id"], "score": row.get("score")})
    prov = dict(out.get("provenance") or {})
    prov["themed_vector_query"] = {
        "ts_utc": _utc_now(),
        "embedding_mode": query_doc.get("embedding_mode"),
        "query_seed": query_doc.get("query_seed"),
        "hits": hits,
        "notes": query_doc.get("notes"),
    }
    out["provenance"] = prov
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--distill", type=Path, default=None)
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args()

    distill_path = args.distill or (ART / f"logos_deep_research_distill_{args.theme}_latest.json")
    query_path = ART / f"logos_themed_vector_query_{args.theme}_latest.json"
    if not distill_path.is_file():
        print(f"Missing distill: {distill_path}", file=sys.stderr)
        return 2
    if not query_path.is_file():
        print(f"Missing query: {query_path}", file=sys.stderr)
        return 2

    distill = json.loads(distill_path.read_text(encoding="utf-8-sig"))
    query_doc = json.loads(query_path.read_text(encoding="utf-8-sig"))
    merged = merge_vector_query(distill, query_doc)

    if args.in_place:
        distill_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out_rel = str(distill_path.relative_to(ROOT)).replace("\\", "/")
    else:
        out_path = ART / f"logos_deep_research_distill_{args.theme}_vector_enriched_latest.json"
        out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out_rel = str(out_path.relative_to(ROOT)).replace("\\", "/")

    print(json.dumps({"ok": True, "out": out_rel, "hits": len(merged["provenance"]["themed_vector_query"]["hits"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
