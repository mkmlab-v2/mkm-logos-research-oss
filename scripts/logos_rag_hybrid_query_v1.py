"""Bilingual (EN+KO) retrieval query builders — Track B only."""
from __future__ import annotations

from typing import Any, Literal

from scripts.run_logos_rag_retrieval_round_v1 import preprocess_query

HybridStyle = Literal[
    "en_ko_concat",
    "ko_en_concat",
    "ko_primary",
    "dual_embed_mean",
]


def build_hybrid_text_query(
    query_en: str,
    query_ko: str,
    *,
    style: HybridStyle = "dual_embed_mean",
) -> tuple[str, str]:
    """Return (effective_text_or_empty, style_applied). ``dual_embed_mean`` uses empty text + dual encode."""
    en = (query_en or "").strip()
    ko = (query_ko or "").strip()
    if style == "ko_primary":
        return preprocess_query(ko), "hybrid_ko_primary"
    if style == "ko_en_concat":
        return preprocess_query(f"{ko}. {en}"), "hybrid_ko_en_concat"
    if style == "en_ko_concat":
        return preprocess_query(f"{en}. {ko}"), "hybrid_en_ko_concat"
    return "", "hybrid_dual_embed_mean"


def encode_hybrid_query(
    model: Any,
    query_en: str,
    query_ko: str,
    *,
    style: HybridStyle = "dual_embed_mean",
) -> list[float]:
    """Encode query for hybrid lane (single string or dual-vector mean)."""
    from scripts.run_logos_rag_retrieval_round_v1 import _encode_query

    text, applied = build_hybrid_text_query(query_en, query_ko, style=style)
    if applied == "hybrid_dual_embed_mean":
        import numpy as np

        en = (query_en or "").strip()
        ko = (query_ko or "").strip()
        v1 = np.asarray(
            model.encode([preprocess_query(ko)], normalize_embeddings=True)[0], dtype=np.float32
        )
        v2 = np.asarray(model.encode([en], normalize_embeddings=True)[0], dtype=np.float32)
        m = (v1 + v2) * 0.5
        n = float(np.linalg.norm(m))
        if n > 0:
            m = m / n
        return m.tolist()
    return _encode_query(model, text)
