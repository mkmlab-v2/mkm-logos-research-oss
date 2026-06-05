#!/usr/bin/env python3
"""Materialize gold q02/q05 router artifacts from live subgraph router [HYPO][research_only].

Replaces post-hoc ``materialize_logos_gold_router_canonical_v1.py`` when runtime
canonicalization (router v1.4+) is SSOT (P1-4 trim).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.materialize_logos_gold_router_canonical_v1 import (  # noqa: E402
    DEFAULT_GOLD,
    REPORT_DIR,
    _gold_item,
    _patch_insight_rag,
    _promote_gold_first,
    _read,
)

ROUTER = ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"
MANIFEST = ROOT / "reports/logos_gold_router_live_materialize_v1_latest.json"
PY = sys.executable


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def materialize_one(
    qid: str,
    gold_doc: dict[str, Any],
    *,
    promote_gold: bool,
    patch_insight_rag: bool,
) -> dict[str, Any]:
    item = _gold_item(gold_doc, qid)
    if not item:
        return {"query_id": qid, "ok": False, "error": "missing gold fixture item"}

    router_path = REPORT_DIR / f"router_{qid}_latest.json"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(
        [
            PY,
            str(ROUTER),
            "--query-id",
            qid,
            "--gold-json",
            str(DEFAULT_GOLD),
            "--top-bridges",
            "6",
            "--output-json",
            str(router_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if cp.returncode != 0:
        return {
            "query_id": qid,
            "ok": False,
            "error": "live router failed",
            "stderr": (cp.stderr or cp.stdout or "")[-800:],
        }

    router = _read(router_path)
    if not router.get("paths"):
        return {"query_id": qid, "ok": False, "error": "live router empty paths"}

    ts = _utc_now()
    if promote_gold:
        router = _promote_gold_first(router, item)

    router["generated_at_utc"] = ts
    router["materialize_meta"] = {
        "schema": "logos_gold_router_live_materialize_v1",
        "query_id": qid,
        "hypothesis_tier": "B",
        "research_only": True,
        "source": "run_logos_subgraph_graphrag_router_v1.py",
        "promote_gold_prefix_first": promote_gold,
        "post_hoc_canonical_skipped": True,
    }
    router_path.write_text(json.dumps(router, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    row: dict[str, Any] = {
        "query_id": qid,
        "ok": True,
        "router_out": str(router_path.relative_to(ROOT)).replace("\\", "/"),
        "verse_id_count": len(router.get("verse_ids") or []),
        "top_verse": (router.get("verse_ids") or [None])[0],
        "lemma_edge_hits": len(router.get("lemma_edge_hits") or []),
        "runtime_canonical": bool((router.get("policy") or {}).get("verse_ref_canonical_at_source")),
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
    rows = [
        materialize_one(
            qid,
            gold_doc,
            promote_gold=args.promote_gold_prefix_first,
            patch_insight_rag=patch_rag,
        )
        for qid in qids
    ]
    ok = all(r.get("ok") for r in rows)

    doc = {
        "schema": "logos_gold_router_live_materialize_v1",
        "generated_at_utc": _utc_now(),
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
