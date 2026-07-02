"""Battery narrative heuristics align with logosInquiryAskDisplayV1.ts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logos_ask_public_narrative_lib_v1 import (  # noqa: E402
    dogma_violation,
    format_public_narrative_paragraphs,
    meets_public_narrative_quality,
    strip_public_research_tags,
)


def test_strip_preserves_newlines_between_paragraphs() -> None:
    sample = "[HYPO] 첫 단락 본문입니다. Rev.21.1 앵커.\n\n두 번째 단락입니다. 새 하늘과 새 땅."
    stripped = strip_public_research_tags(sample)
    assert "\n\n" in stripped
    assert "[HYPO]" not in stripped


def test_meets_narrative_quality_two_paragraphs() -> None:
    body = (
        "요한계시록 21장은 종말 이후 창조 완성의 상징을 다룹니다. "
        "새 하늘과 새 땅은 하나님 거처가 사람과 함께함을 선포합니다. Rev.21.1 앵커.\n\n"
        "새 하늘과 새 땅은 이전 질서의 종료와 하나님 거처의 임재를 가리킵니다. "
        "모든 눈물과 사망이 없어짐을 약속합니다. Rev.21.4."
    )
    q = meets_public_narrative_quality(body)
    assert q["narrative_ok"] is True
    assert int(q["paragraph_count"]) >= 2


def test_format_paragraphs_split_on_double_newline() -> None:
    body = "단락 A — Rev.21.1 관련 설명이 충분히 깁니다.\n\n단락 B — Rev.21.4 새 하늘 상징 설명."
    paras = format_public_narrative_paragraphs(body)
    assert len(paras) >= 2


def test_dogma_allows_scripture_quote_with_bandeusi() -> None:
    sample = (
        "### 한계·주의\n"
        "“내가 반드시 그를 불쌍히 여기리라”(Jer.31.20)는 구절은 심판 이후에도 언약 잔류를 시사합니다."
    )
    assert dogma_violation(sample) is False


def test_dogma_allows_bat_08_style_korean_verse_exposition() -> None:
    sample = (
        "### 반증·대안\n"
        "예레미야 31장 20절은 에브라임에 대한 책망과 긍휼을 드러내며, "
        "“내가 반드시 그를 불쌍히 여기리라”(Jer.31.20)는 메시지를 전한다."
    )
    assert dogma_violation(sample) is False


def test_dogma_allows_trailing_verse_citation_without_quotes() -> None:
    sample = (
        "### 한계·주의\n"
        "하나님의 자비가 여전히 유효함을 시사한다(Jer.31.20)."
    )
    assert dogma_violation(sample) is False


def test_dogma_still_flags_agent_assertion() -> None:
    sample = "적그리스도는 바로 이 인물이며 반드시 지금 나타난다."
    assert dogma_violation(sample) is True


def test_bat_16_disclaimer_not_counted_as_guard_response() -> None:
    from logos_ask_public_narrative_lib_v1 import score_logos_ask_row

    item = {
        "id": "bat_16_gen1_image",
        "query_ko": "창세기 1장 하나님의 형상은 인간 존엄에 대해 무엇을 말하는가?",
        "gold_primary_refs": ["Gen.1.26", "Gen.1.27"],
        "reject_guard_only": True,
    }
    body = (
        "### 핵심 주장\nGraphRAG 보조 — hub primary_verse_refs 우선 · stub 합선 금지.\n\n"
        "### 근거 구절\n- Gen.1.26\n- Gen.1.27\n\n"
        "### 반증·대안\nLLM·Azure Distill로 억지 연결하지 않습니다.\n\n"
        "### 한계·주의\n연구 앵커 기반 요약입니다.\n\n"
        "### 다음 행동 제안\n핵심 구절 1~2개를 지정해 재질문하면 문맥-반증 비교를 더 정밀화할 수 있습니다."
    )
    scored = score_logos_ask_row(
        item,
        body,
        "bigset_topic_genesis6_schools",
        "preset+graphrag_custom+synthesis+inquiry_golden_hub_gen1_image_of_god+reading_pack",
    )
    assert scored["checks"]["guard_only_ok"] is True
    assert scored["quality_pass"] is True


def test_topic_mismatch_guard_still_fails_reject_guard_only() -> None:
    from logos_ask_public_narrative_lib_v1 import score_logos_ask_row

    item = {
        "id": "unit_guard",
        "query_ko": "테스트",
        "gold_primary_refs": ["Rev.13.18"],
        "reject_guard_only": True,
    }
    body = (
        "질문과 검색 경로가 **직접 대응하지 않습니다**. "
        "억지 연결 없이 Rev.13.18 citation lock 앵커로 재질의하세요."
    )
    scored = score_logos_ask_row(item, body, "job_job_suffering_reason", "preset+topic_mismatch_guard")
    assert scored["checks"]["guard_only_ok"] is False


def test_strip_public_tags_before_quality_scoring() -> None:
    from logos_ask_public_narrative_lib_v1 import score_logos_ask_row

    item = {
        "id": "unit_tags",
        "query_ko": "테스트",
        "gold_primary_refs": ["Gen.1.26"],
        "reject_guard_only": True,
    }
    body = (
        "### 핵심 주장\n하나님 형상은 인간 존엄의 근거입니다. Gen.1.26.\n\n"
        "### 근거 구절\n- Gen.1.26\n\n"
        "### 반증·대안\n억지 연결하지 않습니다 [NON_GATING]."
    )
    scored = score_logos_ask_row(item, body, "topic_gen_1_anchor", "preset+graphrag_custom")
    assert scored["checks"]["public_tags_ok"] is True
