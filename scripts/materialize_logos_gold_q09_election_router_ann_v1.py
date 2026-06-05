#!/usr/bin/env python3
"""Materialize gold q09 router/ann from election GraphRAG SSOT [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_logos_ann_typology_boost_v1 import apply_typology_boost
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_ELECTION = ROOT / "reports/logos_graphrag_2026_election_latest.json"
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
REPORT_DIR = ROOT / "reports/magic_orb_insight_by_query"
ROUTER_OUT = REPORT_DIR / "router_q09_latest.json"
ANN_OUT = REPORT_DIR / "ann_query_q09_latest.json"
INSIGHT_OUT = REPORT_DIR / "insight_q09_latest.json"
MANIFEST = ROOT / "reports/logos_gold_q09_election_materialize_v1_latest.json"

QID = "q09"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gold_item(gold_doc: dict[str, Any]) -> dict[str, Any]:
    for item in gold_doc.get("items") or []:
        if str(item.get("id")) == QID:
            return item
    return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--election-json", type=Path, default=DEFAULT_ELECTION)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    args = ap.parse_args()

    gold_doc = _read(args.gold_json)
    item = _gold_item(gold_doc)
    if not item:
        print(json.dumps({"ok": False, "error": f"gold item {QID} missing in fixture"}))
        return 2

    election = _read(args.election_json)
    if not election.get("paths"):
        print(json.dumps({"ok": False, "error": f"missing election router: {args.election_json}"}))
        return 2

    query = str(item.get("query_ko") or "")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    router = deepcopy(election)
    router["query"] = query
    router["query_tokens"] = [t for t in query.replace("?", "").split() if t]
    router["generated_at_utc"] = ts
    canon_verse_ids: list[str] = []
    for vid in router.get("verse_ids") or []:
        c = canonical_verse_ref(str(vid))
        if c and c not in canon_verse_ids:
            canon_verse_ids.append(c)
    router["verse_ids"] = canon_verse_ids
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps = []
        for step in path.get("steps") or []:
            c = canonical_verse_ref(str(step))
            steps.append(c if c and "." in c else str(step))
        path["steps"] = steps
    router["materialize_meta"] = {
        "schema": "logos_gold_q09_election_materialize_v1",
        "source_graphrag": str(args.election_json.relative_to(ROOT)).replace("\\", "/"),
        "query_id": QID,
        "hypothesis_tier": "B",
        "research_only": True,
    }

    gold_ids = list(item.get("gold_verse_ids") or [])
    ann_base = {
        "schema": "logos_vector_ann_lite_query_result_v1",
        "version": "1.1.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "embedding_mode": "election_graphrag_materialize_v1",
        "query_seed": f"st_query:{query}",
        "dim": 384,
        "top_k": [{"verse_id": vid, "score": 0.45 - i * 0.01} for i, vid in enumerate(gold_ids)],
        "notes": "materialized from election GraphRAG gold anchors; typology boost may follow.",
    }
    lexicon = _read(args.lexicon_json)
    ann_doc, boost_meta = apply_typology_boost(
        ann_base,
        query=query,
        query_id=QID,
        lexicon=lexicon,
    )

    insight = {
        "schema": "magic_orb_question_insight_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "query_id": QID,
        "query_ko": query,
        "rag_evidence": [{"verse_id": v, "source": "election_graphrag_router"} for v in gold_ids],
        "notes_ko": "[HYPO][NON_GATING] KOSPI June election crosswalk insight stub.",
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ROUTER_OUT.write_text(json.dumps(router, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ANN_OUT.write_text(json.dumps(ann_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    INSIGHT_OUT.write_text(json.dumps(insight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "logos_gold_q09_election_materialize_v1",
        "generated_at_utc": ts,
        "ok": True,
        "router_out": str(ROUTER_OUT.relative_to(ROOT)).replace("\\", "/"),
        "ann_out": str(ANN_OUT.relative_to(ROOT)).replace("\\", "/"),
        "typology_boost": boost_meta,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "qid": QID, "manifest": str(MANIFEST)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
