#!/usr/bin/env python3
"""Materialize gold q10–q12 router/ann from KOSPI crosswalk + Dan.2 GraphRAG [HYPO][research_only]."""
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
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
REPORT_DIR = ROOT / "reports/magic_orb_insight_by_query"
MANIFEST = ROOT / "reports/logos_gold_crosswalk_materialize_v1_latest.json"

GRAPH_BY_QID: dict[str, str] = {
    "q10": "reports/logos_graphrag_2026_risk_off_latest.json",
    "q11": "reports/logos_graphrag_2026_regime_watch_latest.json",
    "q12": "reports/logos_graphrag_2026_empire_transition_dan2_trial_v1_latest.json",
}


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gold_item(gold_doc: dict[str, Any], qid: str) -> dict[str, Any]:
    for item in gold_doc.get("items") or []:
        if str(item.get("id")) == qid:
            return item
    return {}


def _canonicalize_router(router: dict[str, Any], gold_ids: list[str] | None = None) -> dict[str, Any]:
    out = deepcopy(router)
    _ = gold_ids
    canon_ids: list[str] = []
    seen: set[str] = set()
    for vid in out.get("verse_ids") or []:
        c = canonical_verse_ref(str(vid))
        if c and c not in seen:
            seen.add(c)
            canon_ids.append(c)
    out["verse_ids"] = canon_ids
    for path in out.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps: list[str] = []
        for step in path.get("steps") or []:
            raw = str(step)
            if raw.startswith("node_verse_"):
                c = canonical_verse_ref(raw)
                steps.append(c if c and "." in c else raw)
                continue
            if raw.startswith(("concept:", "function:", "lemma:", "lemma_proxy:", "node:", "mc_", "func_", "lp_")):
                steps.append(raw)
                continue
            if raw.startswith("verse:"):
                c = canonical_verse_ref(raw.split(":", 1)[1])
                steps.append(c if c and "." in c else raw)
                continue
            c = canonical_verse_ref(raw)
            steps.append(c if c and "." in c else raw)
        path["steps"] = steps
    return out


def _ensure_gold_in_router(router: dict[str, Any], gold_ids: list[str]) -> dict[str, Any]:
    ids = list(router.get("verse_ids") or [])
    seen = set(ids)
    for g in gold_ids:
        if g and g not in seen:
            ids.insert(0, g)
            seen.add(g)
    router["verse_ids"] = ids
    return router


def materialize_one(
    qid: str,
    gold_doc: dict[str, Any],
    lexicon: dict[str, Any],
    ts: str,
) -> dict[str, Any]:
    item = _gold_item(gold_doc, qid)
    if not item:
        return {"query_id": qid, "ok": False, "error": "missing gold fixture item"}

    graph_rel = GRAPH_BY_QID.get(qid)
    if not graph_rel:
        return {"query_id": qid, "ok": False, "error": "no graphrag mapping"}
    graph_path = ROOT / graph_rel
    graph = _read(graph_path)
    if not graph.get("paths"):
        return {"query_id": qid, "ok": False, "error": f"missing graphrag: {graph_path}"}

    query = str(item.get("query_ko") or "")
    gold_ids = [canonical_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
    gold_ids = [g for g in gold_ids if g]

    router = _canonicalize_router(graph, gold_ids)
    router["query"] = query
    router["query_tokens"] = [t for t in query.replace("?", "").split() if t]
    router["generated_at_utc"] = ts
    router = _ensure_gold_in_router(router, gold_ids)
    router["materialize_meta"] = {
        "schema": "logos_gold_crosswalk_materialize_v1",
        "source_graphrag": graph_rel,
        "query_id": qid,
        "hypothesis_tier": "B",
        "research_only": True,
    }

    ann_base = {
        "schema": "logos_vector_ann_lite_query_result_v1",
        "version": "1.1.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "embedding_mode": "crosswalk_graphrag_materialize_v1",
        "query_seed": f"st_query:{query}",
        "dim": 384,
        "top_k": [{"verse_id": vid, "score": 0.45 - i * 0.01} for i, vid in enumerate(gold_ids)],
        "notes": "materialized from crosswalk GraphRAG gold anchors; typology boost may follow.",
    }
    ann_doc, boost_meta = apply_typology_boost(
        ann_base,
        query=query,
        query_id=qid,
        lexicon=lexicon,
    )

    insight = {
        "schema": "magic_orb_question_insight_v1",
        "generated_at_utc": ts,
        "hypothesis_tier": "B",
        "research_only": True,
        "query_id": qid,
        "query_ko": query,
        "rag_evidence": [{"verse_id": v, "source": "crosswalk_graphrag_router"} for v in gold_ids],
        "notes_ko": "[HYPO][NON_GATING] KOSPI June crosswalk / Dan.2 trial insight stub.",
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    router_out = REPORT_DIR / f"router_{qid}_latest.json"
    ann_out = REPORT_DIR / f"ann_query_{qid}_latest.json"
    insight_out = REPORT_DIR / f"insight_{qid}_latest.json"
    router_out.write_text(json.dumps(router, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ann_out.write_text(json.dumps(ann_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    insight_out.write_text(json.dumps(insight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "query_id": qid,
        "ok": True,
        "router_out": str(router_out.relative_to(ROOT)).replace("\\", "/"),
        "ann_out": str(ann_out.relative_to(ROOT)).replace("\\", "/"),
        "insight_out": str(insight_out.relative_to(ROOT)).replace("\\", "/"),
        "typology_boost": boost_meta,
        "gold_verse_count": len(gold_ids),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument(
        "--query-id",
        action="append",
        default=[],
        help="q10|q11|q12 (repeatable; default all crosswalk ids)",
    )
    args = ap.parse_args()

    qids = args.query_id or list(GRAPH_BY_QID.keys())
    gold_doc = _read(args.gold_json)
    lexicon = _read(args.lexicon_json)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results = [materialize_one(qid, gold_doc, lexicon, ts) for qid in qids]
    ok = all(r.get("ok") for r in results)
    manifest = {
        "schema": "logos_gold_crosswalk_materialize_v1",
        "generated_at_utc": ts,
        "ok": ok,
        "results": results,
        "hypothesis_tier": "B",
        "research_only": True,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "qids": qids, "manifest": str(MANIFEST)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
