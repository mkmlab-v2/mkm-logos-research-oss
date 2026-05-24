from __future__ import annotations

from scripts.logos_rag_bilingual_query_v1 import (
    effective_retrieval_query_ko_only,
    en_to_ko_map,
)


def test_ko_only_resolves_en_via_map() -> None:
    en_ko = {"covenant stability under crisis": "위기 가운데 언약의 안정과 신실"}
    q, tag = effective_retrieval_query_ko_only(
        raw_q="covenant stability under crisis",
        en_ko=en_ko,
    )
    assert "위기" in q
    assert tag.startswith("ko_only_")


def test_ko_only_prefers_query_ko_arg() -> None:
    q, tag = effective_retrieval_query_ko_only(
        raw_q="covenant stability under crisis",
        query_ko="  위기 가운데 언약  ",
    )
    assert "위기" in q
    assert tag == "ko_only_query_ko_arg"
