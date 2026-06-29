"""PersonaDiary A-Code persona derive + meal menu (Python mirror of TS v1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SURVEY_PACK_PATH = ROOT / "projects/no1kmedi/public/data/clinic_constitution_survey_pack_v1.json"
SURVEY_AXIS_TO_ACODE = {
    "activity_lean": "S",
    "digestion_lean": "L",
    "cold_heat_lean": "L",
    "moisture_lean": "K",
}

PERSONADIARY_ACODE_SCHEMA = "personadiary_acode_persona_v1"

ACODE_META: dict[str, dict[str, str]] = {
    "S1": {
        "axis_label_ko": "스파크",
        "title_ko": "시작 점화형",
        "moment_tone_ko": "짧게 시작하고 바로 몸을 움직여요.",
        "meal_tone_ko": "가볍게 힘 올리는 따뜻한 한 그릇",
    },
    "S2": {
        "axis_label_ko": "스파크",
        "title_ko": "리듬 가속형",
        "moment_tone_ko": "리듬은 올리고 과열은 피하는 날이에요.",
        "meal_tone_ko": "담백 단백질 + 맑은 국물 조합",
    },
    "S3": {
        "axis_label_ko": "스파크",
        "title_ko": "정리 착지형",
        "moment_tone_ko": "마무리 체크리스트를 먼저 붙여요.",
        "meal_tone_ko": "속 편한 국물 + 과하지 않은 탄수화물",
    },
    "L1": {
        "axis_label_ko": "라이프",
        "title_ko": "감각 탐색형",
        "moment_tone_ko": "오늘은 감각과 취향을 가볍게 실험해요.",
        "meal_tone_ko": "산뜻한 채소 + 깔끔한 면/밥",
    },
    "L2": {
        "axis_label_ko": "라이프",
        "title_ko": "실행 몰입형",
        "moment_tone_ko": "한 가지를 고르고 깊게 몰입해요.",
        "meal_tone_ko": "집중 유지용 담백·균형 메뉴",
    },
    "L3": {
        "axis_label_ko": "라이프",
        "title_ko": "회복 정돈형",
        "moment_tone_ko": "속도를 낮추고 숨 고르기를 우선해요.",
        "meal_tone_ko": "부담 적은 죽·수프·부드러운 메뉴",
    },
    "K1": {
        "axis_label_ko": "키핑",
        "title_ko": "기준 세팅형",
        "moment_tone_ko": "오늘 기준 한 줄을 먼저 세워요.",
        "meal_tone_ko": "기본기 있는 따뜻한 집밥 계열",
    },
    "K2": {
        "axis_label_ko": "키핑",
        "title_ko": "균형 유지형",
        "moment_tone_ko": "균형을 지키며 우선순위를 정리해요.",
        "meal_tone_ko": "기름기 낮춘 균형 한 상",
    },
    "K3": {
        "axis_label_ko": "키핑",
        "title_ko": "노이즈 정리형",
        "moment_tone_ko": "잡음을 줄이고 핵심만 남겨요.",
        "meal_tone_ko": "자극 적은 편안한 메뉴",
    },
    "M1": {
        "axis_label_ko": "마인드",
        "title_ko": "관찰 오프닝형",
        "moment_tone_ko": "몸·마음 신호를 가볍게 관찰해요.",
        "meal_tone_ko": "천천히 먹기 좋은 따뜻한 메뉴",
    },
    "M2": {
        "axis_label_ko": "마인드",
        "title_ko": "정서 페이싱형",
        "moment_tone_ko": "감정 리듬을 맞추며 대화를 고릅니다.",
        "meal_tone_ko": "속 편하고 안정감 주는 메뉴",
    },
    "M3": {
        "axis_label_ko": "마인드",
        "title_ko": "휴식 회복형",
        "moment_tone_ko": "쉼을 일정처럼 예약하는 날이에요.",
        "meal_tone_ko": "부드럽고 소화 편한 회복 메뉴",
    },
}

MENU_KEYWORDS = (
    "국밥",
    "곰탕",
    "삼계탕",
    "닭곰탕",
    "미역",
    "찌개",
    "전골",
    "비빔밥",
    "냉면",
    "콩국수",
    "샐러드",
    "죽",
    "덮밥",
    "우동",
    "파스타",
    "칼국수",
    "수제비",
)

LOCATION_NOISE = re.compile(r"[가-힣]+역\s*(근처|인근)?|근처\s*골목[^·—]*")


def _section_lines(package: dict[str, Any], section_id: str) -> list[str]:
    for sec in package.get("sections") or []:
        if isinstance(sec, dict) and sec.get("id") == section_id:
            return [str(ln).strip() for ln in (sec.get("lines") or []) if str(ln).strip()]
    return []


def _axis_scores(package: dict[str, Any]) -> dict[str, int]:
    world = " ".join(_section_lines(package, "world_pulse"))
    life = " ".join(_section_lines(package, "lifestyle"))
    myeongni = " ".join(_section_lines(package, "myeongni"))
    mkm = " ".join(_section_lines(package, "mkm_4ai"))
    return {
        "S": len(re.findall(r"속보|헤드라인|변동|결정|타이밍|기회|리듬", world)),
        "L": len(re.findall(r"스타일|컬러|옷|메뉴|식사|날씨|산책|루틴", life)),
        "K": len(re.findall(r"흐름|균형|정리|기준|집중|확장|수렴", myeongni)),
        "M": len(re.findall(r"마음|페이싱|회복|호흡|코칭|관찰|대화", mkm)),
    }


def _pick_axis(scores: dict[str, int]) -> str:
    order = ("K", "M", "L", "S")
    return max(order, key=lambda axis: scores.get(axis, 0))


def _pick_phase(package: dict[str, Any], survey_responses: dict[str, int] | None = None) -> int:
    seed = "|".join(
        [
            str(package.get("profile_id") or ""),
            str(package.get("calendar_kst") or ""),
            (_section_lines(package, "world_pulse") or [""])[0],
            (_section_lines(package, "myeongni") or [""])[0],
            json.dumps(survey_responses or {}, sort_keys=True),
        ]
    )
    checksum = sum(ord(ch) for ch in seed)
    return (checksum % 3) + 1


def _load_survey_pack() -> dict[str, Any]:
    return json.loads(SURVEY_PACK_PATH.read_text(encoding="utf-8"))


def _survey_boost(survey_responses: dict[str, int] | None) -> dict[str, float]:
    if not survey_responses:
        return {}
    pack = _load_survey_pack()
    scale_max = int((pack.get("scale_default") or {}).get("max", 4))
    axis_totals: dict[str, list[float]] = {}
    for item in pack.get("items") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "")
        axis = str(item.get("axis") or "")
        if item_id not in survey_responses or axis not in SURVEY_AXIS_TO_ACODE:
            continue
        value = int(survey_responses[item_id])
        if value < 0 or value > scale_max:
            continue
        axis_totals.setdefault(axis, []).append(value / scale_max)

    boost: dict[str, float] = {}
    for survey_axis, acode_axis in SURVEY_AXIS_TO_ACODE.items():
        values = axis_totals.get(survey_axis) or []
        if not values:
            continue
        boost[acode_axis] = boost.get(acode_axis, 0.0) + (sum(values) / len(values)) * 2

    fatigue = survey_responses.get("ac02")
    if isinstance(fatigue, int) and fatigue >= 0:
        boost["M"] = boost.get("M", 0.0) + (fatigue / scale_max) * 2
    return boost


def derive_personadiary_acode_profile(
    package: dict[str, Any],
    survey_responses: dict[str, int] | None = None,
) -> dict[str, Any]:
    scores = _axis_scores(package)
    boost = _survey_boost(survey_responses)
    for axis in ("S", "L", "K", "M"):
        scores[axis] += round(boost.get(axis, 0))
    axis = _pick_axis(scores)
    phase = _pick_phase(package, survey_responses)
    cell = f"{axis}{phase}"
    meta = ACODE_META[cell]
    return {
        "schema": PERSONADIARY_ACODE_SCHEMA,
        "preview_only": True,
        "public_code": f"AC-{cell}",
        "cell_code": cell,
        **meta,
    }


def strip_location_from_meal_text(line: str) -> str:
    s = LOCATION_NOISE.sub("", str(line or ""))
    s = re.sub(r"골목\s*[-—–]\s*", "", s)
    s = re.sub(r"맛집\s*[:·]\s*", "", s, flags=re.I)
    return re.sub(r"\s{2,}", " ", s).strip()


def _extract_menu_types(*lines: str) -> str:
    found: list[str] = []
    for line in lines:
        clean = strip_location_from_meal_text(line)
        for kw in MENU_KEYWORDS:
            if kw in clean and kw not in found:
                found.append(kw)
    if found:
        return "·".join(found[:3])
    base = strip_location_from_meal_text(
        next((ln for ln in lines if re.search(r"점심|메뉴|추천|국밥|곰탕", ln)), "")
    )
    if len(base) >= 4:
        return re.sub(r"^점심[:\s]*", "", base, flags=re.I)[:36]
    return "따뜻한 국물"


def _weather_meal_hint(weather: str) -> str | None:
    if re.search(r"무더위|폭염|찌는|3[3-9]°|더움|더워|무덥", weather):
        return "더위엔 맑은 국물·가벼운 단백질"
    if re.search(r"비|장마|흐림|우산", weather):
        return "비 오는 날엔 따뜻한 찌개·전골"
    if re.search(r"쌀쌀|선선|바람|일교차", weather):
        return "쌀쌀하면 구수한 국밥·찜"
    return None


def _news_meal_hint(headline: str) -> str | None:
    if not headline:
        return None
    if re.search(r"코스피|비트코인|ETF|금리|불안|급락|변동|리플|XRP", headline):
        return "뉴스가 복잡할 땐 편안한 한 그릇"
    return None


def _moment_meal_hint(me_line: str) -> str | None:
    m = strip_location_from_meal_text(me_line)
    if not m or len(m) < 6:
        return None
    if re.search(r"숨|쉬|회복|피곤|지침", m):
        return "찰나엔 속 편한 메뉴"
    if re.search(r"관계|마음|대화", m):
        return "마음 쉬며 즐기기 좋은 담백 메뉴"
    return None


def acode_meal_hint(package: dict[str, Any]) -> str:
    acode = derive_personadiary_acode_profile(package)
    return f"{acode['public_code']} {acode['title_ko']} · {acode['meal_tone_ko']}"


def build_moment_meal_menu_recommendation(package: dict[str, Any]) -> str:
    lifestyle = _section_lines(package, "lifestyle")
    world = _section_lines(package, "world_pulse")
    mkm = _section_lines(package, "mkm_4ai")
    myeongni = _section_lines(package, "myeongni")

    weather = next((ln for ln in lifestyle if "날씨" in ln or "°C" in ln), "")
    meal_line = next((ln for ln in lifestyle if re.search(r"점심|메뉴|추천|국밥|곰탕", ln)), "")
    headline = ""
    numbered = next((ln for ln in world if re.match(r"^\d+\.", ln)), None)
    if numbered:
        headline = re.sub(r"^\d+\.\s*", "", numbered)
    elif world:
        headline = world[0]
    me_line = (
        next((ln for ln in myeongni if "오늘 한 줄" in ln), None)
        or next((ln for ln in mkm if "코칭" in ln), None)
        or (myeongni[0] if myeongni else "")
    )

    menu_types = _extract_menu_types(meal_line, "\n".join(mkm), "\n".join(lifestyle))
    reasons = [
        hint
        for hint in (
            _weather_meal_hint(weather),
            acode_meal_hint(package),
            _news_meal_hint(headline),
            _moment_meal_hint(me_line),
        )
        if hint
    ]
    why = " · ".join(reasons[:2]) if reasons else "날씨·오늘 흐름에 맞춘 메뉴"
    return strip_location_from_meal_text(f"{menu_types} — {why}")[:118]
