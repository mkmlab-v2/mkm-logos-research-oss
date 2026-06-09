"""Consumer-facing copy facade for mkmlife news deck & Morning Beans (B-track).

Internal sasang / myeongni / Logos lanes stay in builders; public JSON + UI use
A-Code wellness archetype labels (MAI-style, not MBTI®). SSOT: SDIT_RESEARCH_MEMO §9,
saving_the_news_matrix copy_facade, mkmlife-consumer-vocabulary-v1.ts.
"""
from __future__ import annotations

import re
from typing import Any

_VALID_SASANG = frozenset({"soyang", "taeyang", "taeeum", "soeum"})
_MODE_TO_RHYTHM: dict[str, str] = {
    "idle": "idle",
    "defend": "steady",
    "attack": "drive",
}

# Mirror projects/mkm/mkm-life/lib/mkmlife-consumer-vocabulary-v1.ts (subset)
_ACODE_BY_SASANG_RHYTHM: dict[tuple[str, str], tuple[str, str, str]] = {
    ("taeyang", "spark"): ("A-01", "점화 스파크", "열기와 확장의 리듬 — 과열 시 회복 밴드로 전환"),
    ("taeyang", "drive"): ("A-02", "추진 드라이브", "결단·속도 중심 — 심박·호흡 페이싱 병행"),
    ("taeyang", "blaze"): ("A-03", "확장 블레이즈", "외향 에너지 피크 — 휴식 슬롯 필수"),
    ("soyang", "flow"): ("A-04", "교류 플로우", "대외 소통·순환 리듬 — 과부하 시 페이싱"),
    ("soyang", "link"): ("A-05", "연결 링크", "관계·협업 에너지 — 단독 고강도보다 페어 활동"),
    ("soyang", "pulse"): ("A-06", "리듬 펄스", "변화·기획 밴드 — 안정 식사·수면 루틴 고정"),
    ("taeeum", "anchor"): ("A-07", "중심 앵커", "구조·지지 리듬 — 저항 호흡·브레이싱 적합"),
    ("taeeum", "steady"): ("A-08", "안정 스테디", "지속·체크리스트형 — 급격한 공복·과발한 주의"),
    ("taeeum", "ground"): ("A-09", "대지 그라운드", "하체·코어 안정 — 장시간 앉기·허리 지지"),
    ("soeum", "quiet"): ("A-10", "고요한 코어", "회복·수면·저강도 — 과발한·공격적 단식 회피"),
    ("soeum", "still"): ("A-11", "정적 스틸", "정적 코어·호흡 — 코어·호흡 리듬 우선"),
    ("soeum", "restore"): ("A-12", "회복 리스토어", "성장·회복기 — 규칙적 소식·수분·염분 균형"),
}

_DEFAULT_RHYTHM: dict[str, str] = {
    "taeyang": "spark",
    "soyang": "flow",
    "taeeum": "anchor",
    "soeum": "quiet",
}

DISCLAIMER_DECK_KO = (
    "B-track 관측 덱입니다. 웰니스·인지 부하 참고용이며 투자·실매매·의료 판단을 대체하지 않습니다. "
    "A-Code는 심리검사·체질 확정이 아닙니다 [HYPO]."
)
DISCLAIMER_DECK_EN = (
    "B-track observation deck. Wellness and cognitive-load reference only — "
    "not for trading, medical, or investment decisions. A-Code is not a clinical personality test [HYPO]."
)
DISCLAIMER_MORNING_BEANS_KO = (
    "B-track Morning Beans; 웰니스·자가 관측 참고용이며 의료·법률·투자 조언·실매매 트리거가 아닙니다."
)

PUBLIC_UI_KO = {
    "title": "이벤트 맥락 · 멀티신호 관측",
    "subtitle": "Regime field → signal channels → conflict resolver → observation posture · research_only",
    "banner": "관측 전용 — 투자·의료 조언 아님 · HYPOTHESIS TIER B",
    "lead": "최근 관측 카드를 A-Code 웰니스 리듬·원퀘스천으로 연결합니다. 뉴스 포털·언론사형 피드가 아닙니다.",
    "cta_context_demo": "관측 구 체험",
    "cta_ask_one": "원퀘스천으로",
    "footer_context": "관측 구 체험",
}

PUBLIC_UI_EN = {
    "title": "Event context · multi-signal observability",
    "subtitle": "Regime field → signal channels → conflict resolver → observation posture · research_only",
    "banner": "OBSERVATION ONLY — NOT INVESTMENT OR MEDICAL ADVICE · HYPOTHESIS TIER B",
    "lead": "Recent observation cards link to A-Code wellness rhythm and One-Question — not a news portal.",
    "cta_context_demo": "Context demo",
    "cta_ask_one": "Ask One",
    "footer_context": "Context demo",
}

_LANE_LABEL_KO: dict[str, str] = {
    "field_regime": "거시·운영 관측",
    "personal_wellness": "웰니스 리듬",
    "family_anchor": "가족 리듬",
    "learning": "학습·집중",
    "place_activity": "일정·장소",
    "logos_explain": "맥락 부록 · 비판정",
}

_LENS_SLOT_LABEL_KO: dict[str, str] = {
    "sasang": "신체·리듬 밴드",
    "myeongni": "개인 리듬 프로필",
    "logos": "맥락 부록 · 비판정",
}


def _rhythm_for_sasang(sasang: str, deck_status: str = "WATCH") -> str:
    mode = "idle"
    if deck_status == "HOLD":
        mode = "defend"
    elif deck_status == "WATCH":
        mode = "idle"
    rhythm_key = _MODE_TO_RHYTHM.get(mode, "idle")
    if rhythm_key == "idle":
        return _DEFAULT_RHYTHM.get(sasang, "quiet")
    if rhythm_key == "steady":
        return "steady" if sasang == "taeeum" else _DEFAULT_RHYTHM.get(sasang, "quiet")
    if rhythm_key == "drive":
        return "drive" if sasang == "taeyang" else "pulse"
    return _DEFAULT_RHYTHM.get(sasang, "quiet")


def acode_from_sasang(sasang: str | None, *, deck_status: str = "WATCH") -> dict[str, str]:
    s = (sasang or "taeeum").strip().lower()
    if s not in _VALID_SASANG:
        s = "taeeum"
    rhythm = _rhythm_for_sasang(s, deck_status)
    code_id, name_ko, tagline_ko = _ACODE_BY_SASANG_RHYTHM.get(
        (s, rhythm),
        _ACODE_BY_SASANG_RHYTHM.get((s, _DEFAULT_RHYTHM[s]), ("A-07", "중심 앵커", "")),
    )
    return {
        "consumer_archetype_id": code_id,
        "consumer_display_name_ko": name_ko,
        "consumer_tagline_ko": tagline_ko,
        "signal_channel_label_ko": f"신호 채널 · {name_ko}",
    }


def deck_public_ui(lang: str = "ko") -> dict[str, str]:
    return dict(PUBLIC_UI_EN if lang == "en" else PUBLIC_UI_KO)


def deck_consumer_facade_block() -> dict[str, Any]:
    return {
        "schema": "saving_the_news_public_copy_facade_v1",
        "version": "1.0.0",
        "theology_verse_refs_stripped": True,
        "internal_lens_ids_retained": True,
        "consumer_surface": "a_code_wellness_archetype",
    }


def enrich_deck_card_consumer(
    card: dict[str, Any],
    *,
    deck_status: str = "WATCH",
) -> dict[str, Any]:
    sasang = str(card.get("sasang_accent") or "taeeum")
    card.update(acode_from_sasang(sasang, deck_status=deck_status))
    return card


_THEOLOGY_STRIP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"태양인\s*\([^)]*\)"), "A-Code 관찰 리듬"),
    (re.compile(r"태양인"), "A-Code 관찰 리듬"),
    (re.compile(r"명리\s*앵커\s*—\s*사주\s*기둥"), "개인 리듬 프로필"),
    (re.compile(r"사주\s*기둥"), "프로필 앵커"),
    (re.compile(r"명리"), "리듬"),
    (re.compile(r"Logos"), "맥락 부록"),
    (re.compile(r"성경"), "맥락"),
    (re.compile(r"마법구슬"), "관측 구"),
]


def _strip_theological_surface(text: str) -> str:
    out = text
    for pattern, repl in _THEOLOGY_STRIP_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def facade_morning_beans_card(row: dict[str, Any]) -> dict[str, Any]:
    lane = str(row.get("lane") or "")
    lens = row.get("lens_slot")
    title = str(row.get("title_ko") or "")
    body = str(row.get("body_ko") or "")
    lane_label = _LANE_LABEL_KO.get(lane, lane.replace("_", " "))
    lens_label = _LENS_SLOT_LABEL_KO.get(str(lens), "") if lens else ""

    consumer_title = _strip_theological_surface(title)
    consumer_body = _strip_theological_surface(body)

    if lane == "personal_wellness" and lens == "sasang":
        acode = acode_from_sasang("taeyang")
        consumer_title = f"아침 루틴 · {acode['consumer_archetype_id']} {acode['consumer_display_name_ko']}"
        consumer_body = (
            f"{acode['consumer_tagline_ko']} "
            "따뜻한 수분 → 가벼운 스트레칭 → 첫 작업 전 3분 호흡. "
            "웰니스 자가체크·진단 아님 [HYPO]."
        )
    elif lane == "personal_wellness" and lens == "myeongni":
        consumer_title = "개인 리듬 프로필 · 중기 밴드"
        consumer_body = (
            "프로필 앵커(엔진 Fact) 기반 중기 방향 참고. "
            "운명·매매·임상 단정이 아닙니다."
        )
    elif lane == "logos_explain" or lens == "logos":
        consumer_title = "맥락 부록 · 비판정 채널"
        consumer_body = (
            "의미·서사 맥락 부록 — 사실 합성·매매·송출 트리거가 아닙니다 [NON_GATING]."
        )

    out = dict(row)
    out["consumer_lane_label_ko"] = lane_label
    if lens_label:
        out["consumer_lens_label_ko"] = lens_label
    out["consumer_title_ko"] = consumer_title
    out["consumer_body_ko"] = consumer_body
    out["title_ko"] = consumer_title
    out["body_ko"] = consumer_body
    label = row.get("deep_link_label_ko")
    if isinstance(label, str):
        out["deep_link_label_ko"] = _strip_theological_surface(label)
    return out


def morning_beans_consumer_headlines() -> dict[str, str]:
    return {
        "headline_ko": "아침 10장 · 멀티신호 관측 카드",
        "subline_ko": (
            "A-Code 웰니스 리듬·운영 관측 자세. "
            "무한 스크롤·투자·임상 단정 없음 [HYPO]."
        ),
    }


_ENVELOPE_LOGOS_PUBLIC_TITLE = "맥락 · 연대기 축"
_ENVELOPE_LOGOS_PUBLIC_BODY_FALLBACK = (
    "[NON_GATING] 맥락·연대기 보조 해설. evidence_refs만 연결. 투자·실매매 근거 아님."
)


def envelope_consumer_facade_block() -> dict[str, Any]:
    return {
        "schema": "saving_the_news_public_copy_facade_v1",
        "version": "1.0.0",
        "theology_verse_refs_stripped": True,
        "consumer_surface": "context_sphere_public",
    }


def facade_envelope_logos_lens(lens: dict[str, Any]) -> dict[str, Any]:
    out = dict(lens)
    out["title_ko"] = _ENVELOPE_LOGOS_PUBLIC_TITLE
    body = _strip_theological_surface(str(out.get("body_ko") or ""))
    if any(tok in body for tok in ("성경", "Logos", "사주", "명리", "마법구슬")):
        body = _ENVELOPE_LOGOS_PUBLIC_BODY_FALLBACK
    out["body_ko"] = body
    out["consumer_title_ko"] = _ENVELOPE_LOGOS_PUBLIC_TITLE
    out["consumer_body_ko"] = body
    return out


def facade_public_envelope_consumer(public: dict[str, Any]) -> dict[str, Any]:
    out = dict(public)
    lenses = dict(out.get("lenses") or {})
    if "logos" in lenses:
        lenses["logos"] = facade_envelope_logos_lens(dict(lenses["logos"]))
    out["lenses"] = lenses
    field = dict(out.get("field") or {})
    if field.get("regime_label_ko"):
        field["regime_label_ko"] = "거시·운영 관측 (참고)"
    out["field"] = field
    conflict = dict(out.get("conflict_resolver") or {})
    if conflict.get("summary_ko"):
        conflict["summary_ko"] = _strip_theological_surface(str(conflict["summary_ko"]))
    out["conflict_resolver"] = conflict
    out["consumer_facade"] = envelope_consumer_facade_block()
    return out


_HP_PRIOR_LABELS: dict[str, str] = {
    "sasang_scalar": "A-Code 큐레이션 강도",
    "myeongni_day_pillar_prior_hypo": "개인 리듬 prior",
    "wellness_hypo_budget": "웰니스 예산 [HYPO]",
}

_HP_LENS_SUMMARY_KEYS = ("sasang", "myeongni", "logos")


def facade_hyper_personal_card(card: dict[str, Any]) -> dict[str, Any]:
    out = dict(card)
    priors = []
    for row in out.get("priors_display") or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "")
        priors.append(
            {
                **row,
                "label_ko": _HP_PRIOR_LABELS.get(key, _strip_theological_surface(str(row.get("label_ko") or key))),
            }
        )
    out["priors_display"] = priors
    summaries = dict(out.get("lenses_summary_ko") or {})
    consumer_summaries: dict[str, str | None] = {}
    for lid in _HP_LENS_SUMMARY_KEYS:
        raw = summaries.get(lid)
        if raw is None:
            continue
        consumer_summaries[lid] = _strip_theological_surface(str(raw))
    out["lenses_summary_ko"] = consumer_summaries
    if out.get("one_line_ko"):
        out["one_line_ko"] = _strip_theological_surface(str(out["one_line_ko"]))
    if out.get("disclaimer_ko"):
        out["disclaimer_ko"] = _strip_theological_surface(str(out["disclaimer_ko"]))
    forbidden = [
        "Context appendix is NON_GATING auxiliary only.",
        "Not Track A or CMS promotion proof.",
        "Not live trading or consumer app launch.",
    ]
    out["forbidden"] = forbidden
    out["consumer_facade"] = deck_consumer_facade_block()
    return out
