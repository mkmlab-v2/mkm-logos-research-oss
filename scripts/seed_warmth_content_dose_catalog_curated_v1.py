#!/usr/bin/env python3
"""Seed human-curated WTT dose catalog (Phase 4a · [HYPO])."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/warmth_content_dose_catalog_curated_v1.json"

REVIEWER = "wtt_curator_v1"
REVIEWED_AT = "2026-06-11T07:00:00Z"
EXP = "wtt_epb_pilot_01"


def _dose(
    content_id: str,
    medium: str,
    title_ko: str,
    *,
    intensity: float,
    warmth: float,
    cath: float,
    beta: float,
    recovery: bool,
    style: str,
    risks: list[str],
    rationale: str,
    license_note: str,
    author_ko: str | None = None,
    work_title_ko: str | None = None,
    rights: str = "original_paraphrase",
    spans: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    dose_item: dict[str, Any] = {
        "schema": "warmth_content_dose_v1",
        "version": "1.0.0",
        "dose_version": f"2026-06-11.curated.{content_id}",
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "content_id": content_id,
        "medium": medium,
        "title_ko": title_ko,
        "dose": {
            "intensity_0_1": intensity,
            "warmth_0_1": warmth,
            "catharsis_0_1": cath,
            "narrative_tension_beta_0_1": beta,
            "recovery_arc_present": recovery,
            "delivery_style": style,
            "risk_tags": risks,
        },
        "provenance": {
            "source": "manual_curation",
            "experiment_id": f"{EXP}_curated",
            "slug": "wtt-epb-pilot-01",
        },
    }
    if spans:
        dose_item["narrative_spans_stub"] = spans
    item: dict[str, Any] = {
        "dose_item": dose_item,
        "curator_review": {
            "reviewer": REVIEWER,
            "reviewed_at_utc": REVIEWED_AT,
            "status": "approved",
            "dose_rationale_ko": rationale,
            "license_note": license_note,
        },
    }
    if author_ko or work_title_ko:
        item["content_ref"] = {
            "author_ko": author_ko or "",
            "work_title_ko": work_title_ko or title_ko,
            "rights_status": rights,
        }
    return item


CURATED: list[dict[str, Any]] = [
    _dose(
        "cur_poem_yun_stars",
        "poem",
        "별 헤는 밤 (발췌)",
        intensity=0.32,
        warmth=0.78,
        cath=0.45,
        beta=0.28,
        recovery=True,
        style="warm",
        risks=["low_pressure_only"],
        rationale="저자극·고온 위로. 청소년·소음 프록시에 안전한 서정.",
        license_note="public_domain_author_deceased_1945",
        author_ko="윤동주",
        work_title_ko="별 헤는 밤",
        rights="public_domain",
        spans=[
            {
                "span_id": "s1",
                "text_excerpt_ko": "하늘에 별을 따기 위해 겨울밤이 길어지는 것 같아.",
                "sentiment_sk": 0,
                "icf_stub_code": "b2",
            }
        ],
    ),
    _dose(
        "cur_poem_jeong_fragrance",
        "poem",
        "향기 (발췌)",
        intensity=0.38,
        warmth=0.72,
        cath=0.5,
        beta=0.32,
        recovery=True,
        style="warm",
        risks=[],
        rationale="짧은 이미지·회복 여운. 강한 갈등 없음.",
        license_note="public_domain_modern_ko_poetry",
        author_ko="정지용",
        work_title_ko="향기",
        rights="public_domain",
    ),
    _dose(
        "cur_poem_wildflower",
        "poem",
        "꽃 (들꽃 위로)",
        intensity=0.4,
        warmth=0.7,
        cath=0.55,
        beta=0.35,
        recovery=True,
        style="warm",
        risks=[],
        rationale="소박한 격려. 미지근(under) 보완용.",
        license_note="public_domain_modern_ko_poetry",
        author_ko="한용운",
        work_title_ko="꽃",
        rights="public_domain",
    ),
    _dose(
        "cur_essay_restart_compassion",
        "essay",
        "작은 재시작·자기연민",
        intensity=0.28,
        warmth=0.85,
        cath=0.42,
        beta=0.22,
        recovery=True,
        style="warm",
        risks=["low_pressure_only"],
        rationale="motivation_pool restart 축 중립 패러프레이즈. 죄책 없음.",
        license_note="original_paraphrase_internal",
        rights="original_paraphrase",
        spans=[
            {
                "span_id": "s1",
                "text_excerpt_ko": "오늘 못 한 건 실패가 아니라 조정 신호야.",
                "sentiment_sk": 1,
                "icf_stub_code": "b7",
            }
        ],
    ),
    _dose(
        "cur_short_comeback_short",
        "short_story",
        "짧은 복귀·10분 승리",
        intensity=0.52,
        warmth=0.55,
        cath=0.48,
        beta=0.5,
        recovery=True,
        style="cool",
        risks=["avoid_long_text"],
        rationale="소양 프록시용 짧은 에너지 회복. 장문 회피.",
        license_note="original_paraphrase_internal",
        rights="original_paraphrase",
    ),
    _dose(
        "cur_essay_longview_patience",
        "essay",
        "장기 곡선·꾸준함",
        intensity=0.35,
        warmth=0.62,
        cath=0.4,
        beta=0.3,
        recovery=True,
        style="direct",
        risks=["no_guilt"],
        rationale="태음·장기 스트레스 리프레임. 직설·죄책 없음.",
        license_note="original_paraphrase_internal",
        rights="original_paraphrase",
    ),
    _dose(
        "cur_essay_hope_recovery",
        "essay",
        "어두움 뒤 회복 구간",
        intensity=0.42,
        warmth=0.8,
        cath=0.52,
        beta=0.38,
        recovery=True,
        style="warm",
        risks=["religion_sensitive"],
        rationale="성경 시맨틱 중립 패러프레이즈. 종교 표면어 제거.",
        license_note="original_paraphrase_internal",
        rights="original_paraphrase",
    ),
    _dose(
        "cur_essay_focus_cycle",
        "essay",
        "짧은 집중 블록",
        intensity=0.3,
        warmth=0.5,
        cath=0.35,
        beta=0.25,
        recovery=True,
        style="direct",
        risks=[],
        rationale="과학적 주의 주기. 정서 과열 없이 실용.",
        license_note="original_paraphrase_internal",
        rights="original_paraphrase",
    ),
    _dose(
        "cur_music_lullaby_trad",
        "music_track",
        "전통 자장가(저자극)",
        intensity=0.22,
        warmth=0.88,
        cath=0.3,
        beta=0.15,
        recovery=True,
        style="warm",
        risks=["low_pressure_only"],
        rationale="쿨다운·과부하 후 warm_only arm.",
        license_note="public_domain_folk_placeholder",
        rights="public_domain",
    ),
    _dose(
        "cur_music_gentle_piano",
        "music_track",
        "잔잔한 피아노 연습곡",
        intensity=0.25,
        warmth=0.75,
        cath=0.32,
        beta=0.18,
        recovery=True,
        style="warm",
        risks=[],
        rationale="가사 없음·각성 상승 최소.",
        license_note="licensed_placeholder_streaming_tbd",
        rights="licensed_placeholder",
    ),
    _dose(
        "cur_webtoon_daily_slice",
        "webtoon_episode",
        "일상 슬라이스·저긴장",
        intensity=0.48,
        warmth=0.68,
        cath=0.5,
        beta=0.42,
        recovery=True,
        style="warm",
        risks=[],
        rationale="회복 아크 있는 일상 에피소드(메타만). 실제 작품은 파일럿 시 지정.",
        license_note="licensed_placeholder_title_tbd",
        rights="licensed_placeholder",
    ),
    _dose(
        "cur_webtoon_friend_repair",
        "webtoon_episode",
        "우정 회복 에피소드",
        intensity=0.55,
        warmth=0.72,
        cath=0.58,
        beta=0.48,
        recovery=True,
        style="warm",
        risks=[],
        rationale="갈등 후 화해. catharsis 중간.",
        license_note="licensed_placeholder_title_tbd",
        rights="licensed_placeholder",
    ),
    _dose(
        "cur_novel_little_prince_stub",
        "novel_excerpt",
        "어린 왕자·책임과 돌봄(발췌 스텁)",
        intensity=0.45,
        warmth=0.74,
        cath=0.55,
        beta=0.4,
        recovery=True,
        style="warm",
        risks=[],
        rationale="돌봄·관계 은유. 번역권은 파일럿 전 별도 확인.",
        license_note="translation_rights_tbd",
        author_ko="생텍쥐페리",
        work_title_ko="어린 왕자",
        rights="licensed_placeholder",
    ),
    _dose(
        "cur_short_rainy_small_win",
        "short_story",
        "비 오는 날 작은 성취",
        intensity=0.36,
        warmth=0.76,
        cath=0.44,
        beta=0.3,
        recovery=True,
        style="warm",
        risks=["low_pressure_only"],
        rationale="외로움 완화·작은 승리. teen sweet band 정렬.",
        license_note="original_paraphrase_internal",
        rights="original_paraphrase",
    ),
    _dose(
        "cur_script_evening_self_warmth",
        "script_other",
        "저녁 자기온기 체크인",
        intensity=0.2,
        warmth=0.9,
        cath=0.28,
        beta=0.12,
        recovery=True,
        style="warm",
        risks=["low_pressure_only"],
        rationale="hysteresis_cooldown·over 후 재투여용 최저강도.",
        license_note="original_paraphrase_internal",
        rights="user_generated_stub",
    ),
]


def main() -> int:
    catalog = {
        "schema": "warmth_content_dose_catalog_curated_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "item_count": len(CURATED),
        "items": CURATED,
        "provenance": {
            "source": "seed_warmth_content_dose_catalog_curated_v1",
            "experiment_id": EXP,
            "slug": "wtt-epb-pilot-01",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "item_count": len(CURATED), "out": str(OUT.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
