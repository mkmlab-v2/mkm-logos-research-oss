#!/usr/bin/env python3
"""Encode a Logos Studio query with the same ST model as preset embedding index.

Reproduce:
  py scripts/encode_logos_studio_query_embedding_v1.py --query "네피림 전통"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_INDEX = ROOT / "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default="")
    ap.add_argument("--query-stdin", action="store_true")
    ap.add_argument("--model-id", default="")
    ap.add_argument("--index-json", type=Path, default=DEFAULT_INDEX)
    args = ap.parse_args()
    query = sys.stdin.read() if args.query_stdin else args.query
    query = (query or "").strip()
    if not query:
        print(json.dumps({"ok": False, "error": "empty_query"}, ensure_ascii=False))
        return 1
    model_id = args.model_id.strip()
    if not model_id and args.index_json.is_file():
        idx = json.loads(args.index_json.read_text(encoding="utf-8-sig"))
        model_id = str(idx.get("model_id") or DEFAULT_MODEL)
    if not model_id:
        model_id = DEFAULT_MODEL
    try:
        from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

        model = load_sentence_transformer(model_id)
        vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        out = {
            "ok": True,
            "model_id": model_id,
            "vector_dim": int(vec.shape[0]),
            "vector": vec.tolist(),
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)[:240]}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
