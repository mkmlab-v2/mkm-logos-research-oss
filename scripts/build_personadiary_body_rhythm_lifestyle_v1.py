#!/usr/bin/env python3
"""Build PersonaDiary body-rhythm lifestyle module v1 [HYPO].

Metabolic facts stay literature_supported; ISA/ADIM stays coaching_heuristic.
Product: personadiary.com preview_only — not clinical prescription.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "personadiary_body_rhythm_lifestyle_commander_sample_v1.json"

DISCLAIMER_KO = (
    "[가설][웰니스] 일상 루틴 참고용. 진단·처방·체형·체중 보장 없음. "
    "부분 감량 불가 — 전신 활동·식이 패턴이 우선. "
    "임상·실매매·Track A 합선 없음."
)

AGE_IF_PRESETS: Dict[str, Dict[str, str]] = {
    "20_30": {
        "protocol_ko": "16:8 예시 (8시간 식사창)",
        "note_ko": "고단백·저항+인터벌 병행 시 근손실 완화에 유리할 수 있음 [문헌]",
    },
    "40_50": {
        "protocol_ko": "14:10 또는 16:8 예시",
        "note_ko": "호르몬·인슐린 감수성 회복 목적의 시간 제한 식사 후보 [문헌·개인차]",
    },
    "60_plus": {
        "protocol_ko": "12:12 예시 (식사창 넓게)",
        "note_ko": "끼니당 단백질 분산(예: 0.4g/kg/끼) 우선 — 장시간 단식은 신중 [문헌]",
    },
    "unspecified": {
        "protocol_ko": "12:12~16:8 중 본인 편한 창",
        "note_ko": "의료 상담·만성질환·임신·약물 복용 시 전문가 확인",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def infer_age_band(age_years: Optional[int]) -> str:
    if age_years is None:
        return "unspecified"
    if age_years < 40:
        return "20_30"
    if age_years < 60:
        return "40_50"
    return "60_plus"


def build_body_rhythm(
    *,
    profile_id: str = "commander",
    calendar_kst: str,
    city_key: str = "Seoul",
    age_band: str = "40_50",
    weather_summary_ko: str = "21°C · 양호",
    weather_band: str = "mild",
    personal_color_base_ko: str = "아이보리·베이지·타우프·차콜",
    personal_color_accent_ko: str = "따뜻한 브라운 포인트",
    lunch_ko: str = "닭곰탕",
    lunch_alt_ko: str = "미역·국밥",
    pacing_coaching_ko: str = "회복·페이싱 우선",
    sasang_label_ko: str = "태양인",
) -> Dict[str, Any]:
    if_preset = AGE_IF_PRESETS.get(age_band, AGE_IF_PRESETS["unspecified"])

    meal_fasting = {
        "menu_id": "meal_fasting",
        "title_ko": "식사·금식 창",
        "one_liner_ko": (
            f"{if_preset['protocol_ko']} · 점심 {lunch_ko} 또는 {lunch_alt_ko} · "
            "부분 감량 불가 — 전신 대사 패턴이 우선 [문헌]"
        ),
        "actions_ko": [
            f"식사창: {if_preset['protocol_ko']}",
            f"오늘 한 끼: {lunch_ko} / {lunch_alt_ko} (따뜻한 국물·단백질)",
            "탄수·당 피크 완화: 식사 순서 채소→단백질→탄수 참고",
            if_preset["note_ko"],
        ],
        "avoid_ko": ["공복 아이스커피", "과한 매운 것만", "야식·과당 음료 연속"],
        "evidence_tier": "literature_supported",
        "badge_ko": "[가설][웰니스]",
        "personalization_ko": f"연령대 {age_band} · {pacing_coaching_ko}",
    }

    movement = {
        "menu_id": "movement_10m",
        "title_ko": "10분 움직임",
        "one_liner_ko": (
            "내장지방·대사: 중~고강도 유산소·인터벌이 시간 대비 유리한 경향 [문헌] — "
            f"오늘은 {pacing_coaching_ko}에 맞춰 강도 2단"
        ),
        "actions_ko": [
            "3분: 빠른 걷기 또는 계단 (심박 올리기)",
            "4분: 인터벌 40초 빠르게 / 20초 느리게 ×4",
            "3분: 골반·흉추 가벼운 모빌리티 + 복부 긴장 풀기",
            "크런치 반복 대신 전신·호흡 연결 우선",
        ],
        "avoid_ko": ["통증·어지러움 시 강도 중단", "부위만 타깃한다는 기대"],
        "evidence_tier": "literature_supported",
        "badge_ko": "[가설][웰니스]",
        "personalization_ko": f"날씨 {weather_summary_ko} · 실내·가벼운 레이어 권장",
    }

    style_fit = {
        "menu_id": "style_fit",
        "title_ko": "옷·컬러·핏",
        "one_liner_ko": (
            f"퍼스널 컬러 {personal_color_base_ko} / 포인트 {personal_color_accent_ko} · "
            "몸 편한 실루엣: 복부 긴장·끈 조임 최소"
        ),
        "actions_ko": [
            "상의: 통기 좋은 레이어·허리 과압박 벨트·밴드 피하기",
            "하의: 중간 허리·부드러운 소재 (앉았을 때 복부 압박 완화)",
            f"포인트: {personal_color_accent_ko}",
            "거울 체크: 배를 들이마시지 않은 자연 호흡 자세",
        ],
        "avoid_ko": ["하루 종일 복부 조이기", "불편한 슬림핏 고정"],
        "evidence_tier": "delight",
        "badge_ko": "[가설]",
        "personalization_ko": f"날씨 {weather_band} · 체질 참조 {sasang_label_ko} [은유]",
    }

    breath = {
        "menu_id": "breath_1m",
        "title_ko": "호흡·자세 1분",
        "one_liner_ko": (
            "만성 복부 긴장(배 들이마시기) 습관 완화 drill [코칭 가설] — "
            "의료 처방·체형 보장 아님"
        ),
        "actions_ko": [
            "60초: 코로 천천히 들이마시며 하복부 자연 팽창 허용",
            "길게 내쉬며 갈비 아래 부드럽게 좁혀지기 (과한 복근 쥐어짜기 금지)",
            "책상 앞: 턱 당김·어깨 내림 한 번",
            "목표: 편안한 횡격막 호흡 리듬 (ISA/ZOA 용어는 참고만)",
        ],
        "avoid_ko": ["숨 참으며 복부 조이기", "통증·현기증 시 중단"],
        "evidence_tier": "coaching_heuristic",
        "badge_ko": "[가설][코칭]",
        "personalization_ko": pacing_coaching_ko,
    }

    space_tip = {
        "menu_id": "space_tip",
        "title_ko": "공간 1가지",
        "one_liner_ko": "책상·식탁 — 앉은 자세가 호흡·소화 리듬에 영향을 줄 수 있음 [가설]",
        "actions_ko": [
            "의자: 발바닥 바닥에 닿게, 허리 뒤 얇은 지지",
            "모니터: 눈높이 근처 — 목·흉추 과긴장 완화",
            "식사: 한 번 일어나 2분 걷기 (식후 가벼운 활동)",
        ],
        "avoid_ko": ["구부정 + 복부 조인 채 장시간 고정"],
        "evidence_tier": "coaching_heuristic",
        "badge_ko": "[가설]",
        "personalization_ko": "재택·사무 공통",
    }

    lifestyle_lines = [
        f"몸·리듬 [가설]: {meal_fasting['one_liner_ko']}",
        f"10분 움직임: {movement['actions_ko'][0]} · {movement['actions_ko'][1]}",
        f"호흡 1분: {breath['actions_ko'][0]}",
        f"옷·핏: {style_fit['actions_ko'][0]}",
        f"공간: {space_tip['actions_ko'][0]}",
        "경계: 부분감량·체형 보장·임상 처방 아님 · 전문가 상담 권장",
    ]

    telegram_lines = [
        "",
        "▸ 몸·리듬 (대사·움직임·호흡) [가설][웰니스]",
        f"  식사·금식: {meal_fasting['one_liner_ko']}",
        f"  10분: {' / '.join(movement['actions_ko'][:2])}",
        f"  호흡 1분: {breath['actions_ko'][0]}",
        f"  옷·핏: {style_fit['one_liner_ko']}",
        f"  공간: {space_tip['actions_ko'][0]}",
        f"  {DISCLAIMER_KO}",
    ]

    return {
        "schema": "personadiary_body_rhythm_lifestyle_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "profile_id": profile_id,
        "calendar_kst": calendar_kst,
        "city_key": city_key,
        "age_band": age_band,
        "evidence_mix_ko": "FACT(문헌): 전신 대사·HIIT·IF / COACHING: 호흡·자세·공간 / DELIGHT: 옷·컬러",
        "disclaimer_ko": DISCLAIMER_KO,
        "generated_at_utc": _utc_now(),
        "menus": {
            "meal_fasting": meal_fasting,
            "movement_10m": movement,
            "style_fit": style_fit,
            "breath_1m": breath,
            "space_tip": space_tip,
        },
        "lifestyle_append_lines": lifestyle_lines,
        "telegram_append_lines": telegram_lines,
    }


BODY_RHYTHM_MENU_ORDER = ("meal_fasting", "movement_10m", "style_fit", "breath_1m", "space_tip")


def _menu_to_ui_block(card: Dict[str, Any], key: str) -> Dict[str, Any]:
    body = card.get("one_liner_ko", "") + "\n" + "\n".join(
        f"· {a}" for a in (card.get("actions_ko") or [])
    )
    return {
        "type": "card",
        "title_ko": f"몸·리듬 — {card.get('title_ko', key)}",
        "body_ko": body[:600],
        "badge_ko": card.get("badge_ko", "[가설]"),
        "evidence_tier": card.get("evidence_tier"),
    }


def age_years_from_profile(profile: Dict[str, Any], calendar_kst: str) -> Optional[int]:
    birth = profile.get("birth_anchor") or {}
    instant = str(birth.get("birth_instant_utc") or "").strip()
    if not instant:
        return None
    try:
        born = datetime.fromisoformat(instant.replace("Z", "+00:00"))
        ref = datetime.strptime(calendar_kst[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int((ref - born).days / 365.25)
    except ValueError:
        return None


def build_from_fortune_context(
    *,
    profile: Dict[str, Any],
    fortune: Dict[str, Any],
    lifestyle: Optional[Dict[str, Any]] = None,
    pacing_coaching_ko: str = "회복·페이싱 우선",
) -> Dict[str, Any]:
    lifestyle = lifestyle or fortune.get("lifestyle_concierge") or {}
    calendar_kst = str(fortune.get("calendar_kst") or "")
    profile_id = str(fortune.get("profile_id") or profile.get("subject", {}).get("role") or "commander")
    pc = lifestyle.get("personal_color") or {}
    meals = lifestyle.get("meals") or {}
    weather_cur = lifestyle.get("current") or {}
    weather_summary = str(weather_cur.get("summary_ko") or "21°C · 양호")
    sasang = profile.get("sasang_reference") or {}
    age_band = infer_age_band(age_years_from_profile(profile, calendar_kst))
    return build_body_rhythm(
        profile_id=profile_id,
        calendar_kst=calendar_kst or datetime.now(KST).strftime("%Y-%m-%d"),
        city_key=str(lifestyle.get("city_key") or fortune.get("city_default") or "Seoul"),
        age_band=age_band,
        weather_summary_ko=weather_summary,
        weather_band=str(lifestyle.get("weather_band") or weather_cur.get("band") or "mild"),
        personal_color_base_ko=str(pc.get("base_ko") or "아이보리·베이지"),
        personal_color_accent_ko=str(pc.get("accent_ko") or "따뜻한 브라운 포인트"),
        lunch_ko=str(meals.get("lunch_ko") or "닭곰탕"),
        lunch_alt_ko=str(meals.get("lunch_alt_ko") or "미역·국밥"),
        pacing_coaching_ko=pacing_coaching_ko,
        sasang_label_ko=str(sasang.get("label") or lifestyle.get("sasang_label") or "태양인"),
    )


def merge_into_daily_package(
    package: Dict[str, Any],
    body_rhythm: Dict[str, Any],
    *,
    insert_after_title: str = "오늘의 라이프",
) -> Dict[str, Any]:
    """Return a copy of daily package with body-rhythm woven into lifestyle + ui_blocks."""
    import copy

    out = copy.deepcopy(package)
    append = list(body_rhythm.get("lifestyle_append_lines") or [])

    for sec in out.get("sections") or []:
        if sec.get("id") == "lifestyle":
            sec["lines"] = list(sec.get("lines") or []) + append
            break

    menus = body_rhythm.get("menus") or {}
    blocks = list(out.get("ui_blocks") or [])
    insert_idx = len(blocks)
    for i, block in enumerate(blocks):
        if insert_after_title in str(block.get("title_ko") or ""):
            insert_idx = i + 1
            break

    new_blocks: List[Dict[str, Any]] = []
    for key in BODY_RHYTHM_MENU_ORDER:
        card = menus.get(key) or {}
        if card:
            new_blocks.append(_menu_to_ui_block(card, key))

    out["ui_blocks"] = blocks[:insert_idx] + new_blocks + blocks[insert_idx:]
    upstream = dict(out.get("upstream") or {})
    upstream["body_rhythm"] = body_rhythm
    out["upstream"] = upstream
    concept = str(out.get("concept_ko") or "")
    if "몸·리듬" not in concept:
        out["concept_ko"] = (concept + " · 몸·리듬(식사·움직임·호흡·옷·공간) [가설]").strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-id", default="commander")
    ap.add_argument("--calendar-kst", default="2026-06-07")
    ap.add_argument("--age-years", type=int, default=53)
    ap.add_argument("--lifestyle-json", type=Path, default=ROOT / "reports" / "commander_lifestyle_concierge_latest.json")
    ap.add_argument("--daily-package-json", type=Path, default=ROOT / "docs" / "final" / "artifacts" / "personadiary_daily_response_package_v1_latest.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-daily-out", type=Path, default=ROOT / "docs" / "final" / "artifacts" / "personadiary_daily_response_package_body_rhythm_sample_v1.json")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    lifestyle = _read_json(args.lifestyle_json)
    weather = lifestyle.get("current") or lifestyle
    weather_summary = ""
    if isinstance(weather, dict):
        if weather.get("summary_ko"):
            city = lifestyle.get("city_key") or "Seoul"
            weather_summary = f"{weather.get('summary_ko')}"
            if city:
                weather_summary = f"{city} {weather_summary}" if "°" in str(weather.get("summary_ko", "")) else weather_summary
        elif lifestyle.get("weather_band"):
            weather_summary = str(lifestyle.get("weather_band"))
    if not weather_summary:
        weather_summary = "21°C · 양호"

    pc = lifestyle.get("personal_color") or {}
    meals = lifestyle.get("meals") or {}
    age_band = infer_age_band(args.age_years)

    body = build_body_rhythm(
        profile_id=args.profile_id,
        calendar_kst=args.calendar_kst,
        city_key=str(lifestyle.get("city_key") or "Seoul"),
        age_band=age_band,
        weather_summary_ko=weather_summary.replace("Seoul", "서울") if "Seoul" in weather_summary else weather_summary,
        weather_band=str(lifestyle.get("weather_band") or "mild"),
        personal_color_base_ko=str(pc.get("base_ko") or "아이보리·베이지"),
        personal_color_accent_ko=str(pc.get("accent_ko") or "따뜻한 브라운 포인트"),
        lunch_ko=str(meals.get("lunch_ko") or "닭곰탕"),
        lunch_alt_ko=str(meals.get("lunch_alt_ko") or "미역·국밥"),
        pacing_coaching_ko="회복·페이싱 우선 (소음 AI 보조)",
        sasang_label_ko=str(lifestyle.get("sasang_label") or "태양인"),
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    daily = _read_json(args.daily_package_json)
    if daily:
        merged = merge_into_daily_package(daily, body)
        args.merge_daily_out.parent.mkdir(parents=True, exist_ok=True)
        args.merge_daily_out.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.stdout_only:
        print(json.dumps(body, ensure_ascii=False, indent=2))
    else:
        print(f"WROTE: {args.out_json}")
        if daily:
            print(f"MERGED: {args.merge_daily_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
