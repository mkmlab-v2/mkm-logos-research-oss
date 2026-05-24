"""Bilingual Logos query helpers (v3 EN + KO gloss) — Track B only."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.run_logos_rag_retrieval_round_v1 import preprocess_query

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V3_BILINGUAL = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json"
DEFAULT_V3_EN = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3.json"
DEFAULT_V4_KO_EN = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"

# hybrid sweep winner knobs (comp_logos_rag_hybrid_improvement_sweep_v1)
KO_ONLY_RETRIEVAL_KNOBS = {
    "floor_abs": 0.12,
    "floor_ratio": 0.5,
    "medoid_boost_cap": 0.0,
    "max_k": 24,
    "top_k": 3,
}


def load_bilingual_items(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    items = doc.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"items[] required: {path}")
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        en = str(it.get("query_en") or "").strip()
        ko = str(it.get("query_ko") or "").strip()
        if en and ko:
            out.append(dict(it))
    if not out:
        raise ValueError(f"no bilingual items: {path}")
    return out


def en_to_ko_map(items: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(it["query_en"]).strip(): str(it["query_ko"]).strip()
        for it in items
        if it.get("query_en") and it.get("query_ko")
    }


def ko_queries_from_items(items: list[dict[str, Any]], *, preprocessed: bool = True) -> list[str]:
    out: list[str] = []
    for it in items:
        ko = str(it.get("query_ko") or "").strip()
        if not ko:
            continue
        out.append(preprocess_query(ko) if preprocessed else ko)
    return out


def en_queries_from_items(items: list[dict[str, Any]]) -> list[str]:
    return [str(it["query_en"]).strip() for it in items if it.get("query_en")]


def resolve_ko_gloss(
    *,
    raw_q: str,
    query_en: str = "",
    query_ko: str = "",
    en_ko: dict[str, str] | None = None,
) -> tuple[str | None, str]:
    """Return (ko_gloss, resolution_tag)."""
    ko = (query_ko or "").strip()
    if ko:
        return ko, "query_ko_arg"
    en = (query_en or "").strip()
    if en and en_ko and en in en_ko:
        return en_ko[en], "en_key_lookup"
    raw = (raw_q or "").strip()
    if raw and en_ko and raw in en_ko:
        return en_ko[raw], "raw_en_lookup"
    return None, "missing_ko_gloss"


def effective_retrieval_query_ko_only(
    *,
    raw_q: str,
    query_en: str = "",
    query_ko: str = "",
    en_ko: dict[str, str] | None = None,
) -> tuple[str, str]:
    """KO-only route: preprocess KO gloss when available."""
    from scripts.logos_rag_query_route_v1 import hangul_syllable_count

    ko, tag = resolve_ko_gloss(
        raw_q=raw_q, query_en=query_en, query_ko=query_ko, en_ko=en_ko
    )
    if ko:
        return preprocess_query(ko), f"ko_only_{tag}"
    if hangul_syllable_count(raw_q) > 0:
        return preprocess_query(raw_q.strip()), "ko_only_raw_hangul"
    return raw_q.strip(), "ko_only_en_no_map"
