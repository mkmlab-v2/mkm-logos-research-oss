#!/usr/bin/env python3
"""Bootstrap human gold candidates from KO retrieval (top-5 pack + optional top-1 fill)."""
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

from scripts.logos_rag_query_route_v1 import build_retrieval_query, detect_query_route  # noqa: E402
from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_SQLITE,
    _encode_query,
    _load_index,
    _retrieve_baseline,
    _score_all,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_PACK = PILOT / "logos_rag_human_adjudication_pack_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_items(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    items = doc.get("items")
    if not isinstance(items, list):
        raise ValueError("items[] required")
    return doc, [x for x in items if isinstance(x, dict)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--pack-out", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument(
        "--fill-empty-with-top1",
        action="store_true",
        help="Set gold_verse_ids_human to KO top-1 when empty (bootstrap; requires human review).",
    )
    args = ap.parse_args()

    if not args.gold_json.is_file():
        print(f"Missing: {args.gold_json}", file=sys.stderr)
        return 2
    if not args.sqlite.is_file():
        print(f"Missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2

    doc, items = _load_items(args.gold_json)
    index_rows, dim, _mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)

    pack_rows: list[dict[str, Any]] = []
    filled = 0
    for it in items:
        qid = str(it.get("id") or "")
        ko = str(it.get("query_ko") or "").strip()
        route = detect_query_route(ko, policy="auto")
        rq, applied = build_retrieval_query(ko, route)
        qvec = _encode_query(model, rq)
        scored = _score_all(qvec, index_rows, dim)
        hits = _retrieve_baseline(scored, 5)
        top1 = hits[0]["verse_id"] if hits else None
        pack_rows.append(
            {
                "id": qid,
                "query_ko": ko,
                "route": route,
                "retrieval_query": rq,
                "candidates_top5": hits,
            }
        )
        existing = it.get("gold_verse_ids_human") or []
        has_human = isinstance(existing, list) and any(
            isinstance(x, str) and x.strip() for x in existing
        )
        if args.fill_empty_with_top1 and not has_human and isinstance(top1, str):
            it["gold_verse_ids_human"] = [top1]
            it["adjudication_status"] = "bootstrap_top1_pending_review"
            it["adjudication_note"] = "Auto from KO retrieval top-1; replace after human review."
            filled += 1
        elif has_human:
            it["adjudication_status"] = it.get("adjudication_status") or "human_confirmed"

    doc["status"] = "bootstrap_top1_pending_review" if args.fill_empty_with_top1 else doc.get("status")
    doc["updated_at_utc"] = _utc_now()
    doc["items"] = items
    args.gold_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pack = {
        "schema": "logos_rag_human_adjudication_pack_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "sqlite": str(args.sqlite.resolve()),
        "items": pack_rows,
        "note": "Pick gold_verse_ids_human from candidates_top5; do not treat bootstrap as Track A proof.",
    }
    args.pack_out.parent.mkdir(parents=True, exist_ok=True)
    args.pack_out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "gold_json": str(args.gold_json),
                "pack_out": str(args.pack_out),
                "filled_top1": filled,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
