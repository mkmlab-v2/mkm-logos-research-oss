from __future__ import annotations

from scripts.logos_rag_query_route_v1 import build_retrieval_query, detect_query_route, hangul_ratio


def test_hangul_ratio_ko_only() -> None:
    assert hangul_ratio("위기 속 언약") > 0.5


def test_detect_ko() -> None:
    assert detect_query_route("위기 가운데 언약의 안정", policy="auto") == "ko"


def test_detect_en() -> None:
    assert detect_query_route("covenant stability under crisis", policy="auto") == "en"


def test_detect_mixed() -> None:
    assert detect_query_route("covenant 위기 stability", policy="auto") == "mixed_raw"


def test_build_ko_preprocess() -> None:
    q, applied = build_retrieval_query("  위기  ", "ko")
    assert applied == "ko"
    assert "위기" in q


def test_detect_ko_only_policy() -> None:
    assert detect_query_route("anything", policy="ko_only") == "ko_only"
