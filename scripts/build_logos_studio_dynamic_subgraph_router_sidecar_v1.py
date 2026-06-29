#!/usr/bin/env python3
"""Build dynamic subgraph router sidecar for Logos Studio (P6).

Merges query-time router output + bloom secondary fetch hints per preset/gold query.
  py scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py
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

from scripts.logos_studio_bloom_secondary_fetch_lib_v1 import expand_verse_refs_via_bloom, load_bloom_index
from scripts.run_logos_subgraph_graphrag_router_v1 import (  # noqa: E402
    DEFAULT_GEMATRIA_LEXICON,
    DEFAULT_LEMMA,
    DEFAULT_OSI_XREF,
    DEFAULT_REGISTRY,
    DEFAULT_SEED_CHAIN,
    DEFAULT_SINEW_XREF,
    DEFAULT_THEOGRAPHIC_ENTITY,
    _load_json,
    _load_jsonl,
    route,
)

BLOOM = ROOT / "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json"
PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
OUT_ART = ROOT / "docs/final/artifacts/logos_studio_dynamic_subgraph_router_v1_latest.json"
OUT_PUB = ROOT / "projects/no1kmedi/public/data/logos_studio/dynamic_subgraph_router_v1.json"

SCHEMA = "logos_studio_dynamic_subgraph_router_v1"
_ROUTER_CTX: dict[str, Any] | None = None


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _router_ctx() -> dict[str, Any]:
    global _ROUTER_CTX
    if _ROUTER_CTX is None:
        _ROUTER_CTX = {
            "registry": _load_json(DEFAULT_REGISTRY) or {},
            "lemma_rows": _load_jsonl(DEFAULT_LEMMA),
            "seed_chain": _load_json(DEFAULT_SEED_CHAIN),
            "gematria_rows": _load_jsonl(DEFAULT_GEMATRIA_LEXICON),
            "sinew_rows": _load_jsonl(DEFAULT_SINEW_XREF),
            "osi_rows": _load_jsonl(DEFAULT_OSI_XREF),
            "theographic_rows": _load_jsonl(DEFAULT_THEOGRAPHIC_ENTITY),
        }
    return _ROUTER_CTX


def _run_router(query: str) -> dict[str, Any]:
    ctx = _router_ctx()
    return route(
        query,
        registry=ctx["registry"],
        lemma_rows=ctx["lemma_rows"],
        seed_chain=ctx["seed_chain"],
        gematria_lexicon_rows=ctx["gematria_rows"],
        sinew_rows=ctx["sinew_rows"],
        osi_rows=ctx["osi_rows"],
        theographic_rows=ctx["theographic_rows"],
        top_bridges=3,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-presets", type=int, default=0)
    args = ap.parse_args()

    bloom = load_bloom_index(BLOOM) or {}
    presets_doc = json.loads(PRESETS.read_text(encoding="utf-8-sig")) if PRESETS.is_file() else {"presets": []}
    gold_doc = json.loads(GOLD.read_text(encoding="utf-8-sig")) if GOLD.is_file() else {"queries": []}

    routes: dict[str, Any] = {}
    queries: list[tuple[str, str]] = []

    for preset in presets_doc.get("presets") or []:
        if not isinstance(preset, dict):
            continue
        pid = str(preset.get("id") or "")
        q = str(preset.get("prompt_ko") or preset.get("query_ko") or "")
        if pid and q:
            queries.append((pid, q))

    for row in gold_doc.get("queries") or []:
        if not isinstance(row, dict):
            continue
        qid = str(row.get("query_id") or row.get("id") or "")
        q = str(row.get("query_ko") or row.get("query") or "")
        if qid and q:
            queries.append((f"gold_{qid}", q))

    if args.max_presets > 0:
        queries = queries[: args.max_presets]

    for route_id, query in queries:
        router_doc = _run_router(query)
        base_refs = list(router_doc.get("verse_ids") or [])
        expanded, bloom_meta = expand_verse_refs_via_bloom(query, base_refs, bloom, max_extra=32)
        routes[route_id] = {
            "query_ko": query,
            "bridges_matched": int(router_doc.get("bridges_matched") or 0),
            "paths_count": len(router_doc.get("paths") or []),
            "verse_refs_primary": base_refs[:48],
            "verse_refs_expanded": expanded[:64],
            "bloom_secondary_fetch": bloom_meta,
            "dynamic_subgraph": True,
        }

    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "route_count": len(routes),
        "bloom_index_present": bool(bloom),
        "routes": routes,
        "reproduce": "py scripts/build_logos_studio_dynamic_subgraph_router_sidecar_v1.py",
    }

    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_PUB.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(payload, encoding="utf-8")
    OUT_PUB.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "route_count": len(routes), "out": str(OUT_ART)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
