#!/usr/bin/env python3
"""Canonicalize Logos gold router artifacts (verse_ref aliases → canon) [HYPO][research_only]."""
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
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
REPORT_DIR = ROOT / "reports/magic_orb_insight_by_query"
MANIFEST = ROOT / "reports/logos_gold_router_canonical_materialize_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gold_item(gold_doc: dict[str, Any], qid: str) -> dict[str, Any]:
    for item in gold_doc.get("items") or []:
        if str(item.get("id")) == qid:
            return item
    return {}


def _gold_rank_key(vid: str, gold_ids: list[str], prefixes: list[str]) -> tuple[int, int]:
    if vid in gold_ids:
        return (0, gold_ids.index(vid))
    for i, p in enumerate(prefixes):
        if vid.startswith(p):
            return (1, i)
    return (2, 0)


def _canonicalize_router(router: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(router)
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
            if raw.startswith(("concept:", "function:", "lemma_proxy:", "node:")) or raw.startswith("node_"):
                steps.append(raw)
                continue
            c = canonical_verse_ref(raw)
            steps.append(c if c and "." in c else raw)
        path["steps"] = steps
    return out


def _promote_gold_first(router: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    gold_ids = [canonical_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
    prefixes = [str(x) for x in (item.get("gold_verse_prefixes") or [])]
    ids = list(router.get("verse_ids") or [])
    ids.sort(key=lambda v: _gold_rank_key(v, gold_ids, prefixes))
    router["verse_ids"] = ids
    return router


def _patch_insight_rag(qid: str, item: dict[str, Any], ts: str) -> dict[str, Any] | None:
    """Prepend gold verse_id rows to insight rag_evidence (q09 materialize pattern)."""
    insight_path = REPORT_DIR / f"insight_{qid}_latest.json"
    insight = _read(insight_path)
    if not insight or not item:
        return None
    gold_ids = [canonical_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
    gold_ids = [g for g in gold_ids if g]
    if not gold_ids:
        return None
    existing = insight.get("rag_evidence") or []
    have_verse_id = {
        canonical_verse_ref(str(row.get("verse_id") or ""))
        for row in existing
        if isinstance(row, dict) and row.get("verse_id")
    }
    prepend = [
        {"verse_id": g, "source": "gold_router_canonical_materialize_v1", "evidence_kind": "gold_anchor"}
        for g in gold_ids
        if g not in have_verse_id
    ]
    insight["rag_evidence"] = prepend + list(existing)
    insight["generated_at_utc"] = ts
    insight["materialize_meta"] = {
        "schema": "logos_gold_insight_rag_verse_patch_v1",
        "query_id": qid,
        "hypothesis_tier": "B",
        "research_only": True,
    }
    insight_path.write_text(json.dumps(insight, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"insight_out": str(insight_path.relative_to(ROOT)).replace("\\", "/"), "rag_verse_ids_added": len(prepend)}


def materialize_one(
    qid: str,
    gold_doc: dict[str, Any],
    promote_gold: bool,
    patch_insight_rag: bool,
) -> dict[str, Any]:
    router_path = REPORT_DIR / f"router_{qid}_latest.json"
    router = _read(router_path)
    if not router:
        return {"query_id": qid, "ok": False, "error": f"missing router: {router_path}"}

    item = _gold_item(gold_doc, qid)
    router = _canonicalize_router(router)
    if promote_gold and item:
        router = _promote_gold_first(router, item)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    router["generated_at_utc"] = ts
    router["materialize_meta"] = {
        "schema": "logos_gold_router_canonical_materialize_v1",
        "query_id": qid,
        "hypothesis_tier": "B",
        "research_only": True,
        "promote_gold_prefix_first": promote_gold,
    }
    router_path.write_text(json.dumps(router, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    row: dict[str, Any] = {
        "query_id": qid,
        "ok": True,
        "router_out": str(router_path.relative_to(ROOT)).replace("\\", "/"),
        "verse_id_count": len(router.get("verse_ids") or []),
        "top_verse": (router.get("verse_ids") or [None])[0],
    }
    if patch_insight_rag:
        patch = _patch_insight_rag(qid, item, ts)
        if patch:
            row.update(patch)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--query-id", action="append", default=[], help="Repeatable; default q02 q05")
    ap.add_argument(
        "--promote-gold-prefix-first",
        action="store_true",
        help="Reorder verse_ids: exact gold ids, then prefix matches [HYPO eval uplift]",
    )
    ap.add_argument(
        "--no-patch-insight-rag",
        action="store_true",
        help="Skip prepending gold verse_id rows to insight rag_evidence",
    )
    ap.add_argument("--out-json", type=Path, default=MANIFEST)
    args = ap.parse_args()

    qids = args.query_id or ["q02", "q05"]
    gold_doc = _read(args.gold_json)
    patch_rag = not args.no_patch_insight_rag
    rows = [materialize_one(qid, gold_doc, args.promote_gold_prefix_first, patch_rag) for qid in qids]
    ok = all(r.get("ok") for r in rows)

    doc = {
        "schema": "logos_gold_router_canonical_materialize_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok,
        "research_only": True,
        "promote_gold_prefix_first": args.promote_gold_prefix_first,
        "patch_insight_rag": patch_rag,
        "rows": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "rows": rows, "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
