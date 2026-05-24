"""Query routing for Logos RAG (KO / EN / hybrid) — Track B only."""
from __future__ import annotations

import re
from typing import Literal

from scripts.run_logos_rag_retrieval_round_v1 import preprocess_query

QueryRoute = Literal["en", "ko", "hybrid", "mixed_raw", "ko_only"]

_HANGUL = re.compile(r"[\uAC00-\uD7A3]")
_LATIN = re.compile(r"[A-Za-z]")


def hangul_syllable_count(text: str) -> int:
    return len(_HANGUL.findall(text or ""))


def hangul_ratio(text: str) -> float:
    t = text or ""
    if not t.strip():
        return 0.0
    h = hangul_syllable_count(t)
    latin = len(_LATIN.findall(t))
    denom = h + latin
    return h / denom if denom else 0.0


def detect_query_route(raw: str, *, policy: str = "auto") -> QueryRoute:
    """auto: hangul+latin → mixed_raw; hangul-only → ko; else en."""
    p = (policy or "auto").strip().lower()
    if p in ("en", "ko", "hybrid", "mixed_raw", "ko_only"):
        return p  # type: ignore[return-value]
    t = (raw or "").strip()
    has_h = hangul_syllable_count(t) > 0
    has_l = bool(_LATIN.search(t))
    if has_h and has_l:
        return "mixed_raw"
    if has_h:
        return "ko"
    return "en"


def build_retrieval_query(raw: str, route: QueryRoute) -> tuple[str, str]:
    """Return (effective_query, route_applied)."""
    t = (raw or "").strip()
    if route == "ko_only":
        # Caller should use logos_rag_bilingual_query_v1.effective_retrieval_query_ko_only
        # when EN gloss map is required; here: hangul raw or preprocess fallback.
        if hangul_syllable_count(t) > 0:
            return preprocess_query(t), "ko_only_hangul"
        return t, "ko_only_pass_through"
    if route == "ko":
        return preprocess_query(t), "ko"
    if route == "en":
        return t, "en"
    if route == "hybrid":
        # Legacy single-string hybrid: prefer preprocess (concat). For structured EN+KO use
        # logos_rag_hybrid_query_v1.build_hybrid_text_query / encode_hybrid_query (default dual_embed_mean).
        return preprocess_query(t), "hybrid"
    return preprocess_query(t), "mixed_raw"
