"""PersonaDiary consumer copy helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import personadiary_consumer_copy_v1 as cc  # noqa: E402


def test_pick_meal_lines_prioritizes_lunch() -> None:
    lines = [
        "날씨·서울: 16°C · 양호",
        "퍼스널 컬러: 아이보리",
        "점심 추천: 닭곰탕 또는 미역·국밥",
        "피하기: 과한 매운 것",
    ]
    picked = cc.pick_meal_lines(lines)
    assert picked[0].startswith("점심 추천")


def test_build_moment_summary_meal_prefers_lunch() -> None:
    cards = [
        {
            "section_id": "lifestyle",
            "body_ko": "날씨·서울: 16°C\n점심 추천: 닭곰탕",
        },
        {"section_id": "myeongni", "body_ko": "오늘의 흐름 테스트"},
    ]
    summary = cc.build_moment_summary_ko(intent="meal", cards=cards)
    assert "점심 추천" in summary
    assert "닭곰탕" in summary


def test_consumer_hero_strips_ops_jargon() -> None:
    body = cc.build_consumer_hero_body(
        fusion_line="나: 작전(파수) — 마감 · 판: HOLD → 말·결정은 짧게, 페이싱 우선",
        myeongni_first="오늘 한 줄: 균형·흐름을 동시에 보되 과확장은 경계",
        lifestyle_lines=["날씨·서울: 16°C · 양호", "점심 추천: 국밥"],
        calendar_kst="2026-06-06",
        city="Seoul",
    )
    assert "작전" not in body
    assert "16°C" in body or "페이싱" in body or "균형" in body


def test_forbidden_substring_blocks_without_negation() -> None:
    violations = cc.find_forbidden_violations("오늘 운세는 좋습니다")
    assert any("운세" in v for v in violations)


def test_forbidden_substring_allows_negation_disclaimer() -> None:
    violations = cc.find_forbidden_violations("예언·적중 아님 · 성찰 일기")
    assert violations == []


def test_sanitize_replaces_ilun_with_flow() -> None:
    out = cc.sanitize_consumer_fragment("명리 일운: 균형", strict=False)
    assert "일운" not in out
    assert "오늘의 흐름" in out


def test_assert_consumer_safe_rejects_percent_claim() -> None:
    try:
        cc.assert_consumer_safe("내일 비 올 확률 80%")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "consumer_copy_unsafe" in str(exc)


def test_copy_contract_json_loads() -> None:
    doc = cc.load_copy_contract()
    assert doc.get("schema") == "personadiary_non_prediction_copy_contract_v1"
    assert len(cc.allowed_lines_ko()) >= 5
    assert doc.get("anchor_line_ko")
    assert doc.get("phase_disclaimers", {}).get("v0_9_fact")


def test_allowed_lines_are_consumer_safe() -> None:
    for line in cc.allowed_lines_ko():
        cc.assert_consumer_safe(line)


def test_hybrid_overclaim_blocked() -> None:
    for bad in (
        "스크린타임 불필요 — 앱 하나로 끝",
        "군사등급 완벽 차단",
        "우회 불가 인지 방화벽",
    ):
        violations = cc.find_forbidden_violations(bad)
        assert violations, bad


def test_hybrid_framing_allowed_when_no_overclaim() -> None:
    ok_line = "귀찮은 스크린타임 설정판을 인생 레인 1탭으로 대체하는 인지 통제 두뇌"
    assert cc.find_forbidden_violations(ok_line) == []


def test_personadiary_copy_ts_surfaces_safe() -> None:
    ts_path = ROOT / "projects/no1kmedi/src/content/personadiaryCopy.ts"
    text = ts_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not any(k in stripped for k in ('title:', "description:", "conceptKo:")):
            continue
        if "아님" in line or "아닙니다" in line or "단정 없" in line:
            continue
        violations = cc.find_forbidden_violations(line)
        assert not violations, f"{line!r} -> {violations}"
