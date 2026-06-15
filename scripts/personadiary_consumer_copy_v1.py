"""PersonaDiary consumer-facing copy helpers (deterministic, no LLM)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
COPY_CONTRACT_JSON = (
    ROOT / "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json"
)

_OPS_SKIP = re.compile(
    r"작전\(|Fact-Lock|Track A|신규 RAG|preview_only|research_only|무관\s*$",
    re.I,
)
_TAG_RE = re.compile(r"\[(?:가설|NON_GATING|HYPO)[^\]]*\]", re.I)

_MEAL_PRIMARY = (
    "점심 추천",
    "점심:",
    "저녁",
    "아침",
    "메뉴",
    "국밥",
    "곰탕",
    "맛집",
    "피하기",
)
_MEAL_SECONDARY = ("날씨", "컬러", "스타일", "퍼스널")

_DEFAULT_FORBIDDEN_SUBSTRINGS = (
    "적중률",
    "적중",
    "운세",
    "forecast",
    "prophecy",
    "hit rate",
    "Brier",
    "일운",
)
_DEFAULT_FORBIDDEN_REGEX = (r"\d\s*%", r"\d+%")
_DEFAULT_NEGATION_EXEMPT = (
    "아님",
    "아닙니다",
    "없음",
    "금지",
    "단정 없",
    "하지 않",
    "not a",
    "no forecast",
)


def load_copy_contract() -> dict:
    if not COPY_CONTRACT_JSON.is_file():
        return {}
    return json.loads(COPY_CONTRACT_JSON.read_text(encoding="utf-8"))


def forbidden_substrings() -> tuple[str, ...]:
    doc = load_copy_contract()
    raw = doc.get("forbidden_substrings") or list(_DEFAULT_FORBIDDEN_SUBSTRINGS)
    return tuple(str(x) for x in raw)


def forbidden_regexes() -> tuple[re.Pattern[str], ...]:
    doc = load_copy_contract()
    patterns = doc.get("forbidden_regex") or list(_DEFAULT_FORBIDDEN_REGEX)
    return tuple(re.compile(p, re.I) for p in patterns)


def negation_exempt_phrases() -> tuple[str, ...]:
    doc = load_copy_contract()
    raw = doc.get("negation_exempt_phrases") or list(_DEFAULT_NEGATION_EXEMPT)
    return tuple(str(x) for x in raw)


def _fragment_has_negation_exempt(text: str) -> bool:
    lowered = text.lower()
    return any(ex.lower() in lowered for ex in negation_exempt_phrases())


def find_forbidden_violations(text: str) -> list[str]:
    """Return human-readable violation codes for consumer-facing copy."""
    s = str(text or "")
    if not s.strip():
        return []
    if _fragment_has_negation_exempt(s):
        return []

    violations: list[str] = []
    for token in forbidden_substrings():
        if token.lower() in s.lower():
            violations.append(f"forbidden_substring:{token}")
    for pat in forbidden_regexes():
        if pat.search(s):
            violations.append(f"forbidden_regex:{pat.pattern}")
    if "예언" in s and not _fragment_has_negation_exempt(s):
        violations.append("forbidden_substring:예언")
    return violations


def assert_consumer_safe(text: str) -> None:
    violations = find_forbidden_violations(text)
    if violations:
        raise ValueError(f"consumer_copy_unsafe: {', '.join(violations)}")


def scan_text_for_forbidden(text: str) -> dict:
    violations = find_forbidden_violations(text)
    return {"ok": len(violations) == 0, "violations": violations}


def allowed_lines_ko() -> list[str]:
    doc = load_copy_contract()
    lines = doc.get("allowed_lines_ko")
    if isinstance(lines, list) and lines:
        return [str(x) for x in lines]
    return []


def apply_ui_replacements(text: str) -> str:
    doc = load_copy_contract()
    mapping = doc.get("ui_replacement_map") or {"일운": "오늘의 흐름", "운세": "리듬·성찰"}
    s = str(text or "")
    for src, dst in mapping.items():
        s = s.replace(str(src), str(dst))
    return s


def sanitize_consumer_fragment(text: str, *, max_len: int = 200, strict: bool = False) -> str:
    s = _TAG_RE.sub("", str(text or ""))
    s = re.sub(r"작전\([^)]*\)", "", s)
    s = apply_ui_replacements(s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*·\s*", " · ", s).strip(" ·")
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    if strict:
        assert_consumer_safe(s)
    return s


def meal_line_score(line: str) -> int:
    for i, key in enumerate(_MEAL_PRIMARY):
        if key in line:
            return 200 - i
    for i, key in enumerate(_MEAL_SECONDARY):
        if key in line:
            return 80 - i
    return 0


def pick_meal_lines(lines: Iterable[str], *, max_lines: int = 4) -> list[str]:
    ordered = list(lines)
    if not ordered:
        return []
    scored = sorted(
        ordered,
        key=lambda ln: (-meal_line_score(ln), ordered.index(ln)),
    )
    picked = [ln for ln in scored if meal_line_score(ln) > 0]
    return (picked or ordered)[:max_lines]


def pick_weather_lines(lines: Iterable[str], *, max_lines: int = 4) -> list[str]:
    ordered = list(lines)
    keys = ("날씨", "컬러", "스타일", "옷", "°", "퍼스널")
    picked = [ln for ln in ordered if any(k in ln for k in keys)]
    return (picked or ordered)[:max_lines]


def pick_lines_for_intent(lines: list[str], *, intent: str, max_lines: int = 4) -> list[str]:
    if intent == "meal":
        return pick_meal_lines(lines, max_lines=max_lines)
    if intent == "weather_fit":
        return pick_weather_lines(lines, max_lines=max_lines)
    return lines[:max_lines]


def first_meal_summary_line(cards: list[dict]) -> str:
    for card in cards:
        if card.get("section_id") != "lifestyle":
            continue
        for ln in str(card.get("body_ko") or "").split("\n"):
            ln = sanitize_consumer_fragment(ln, max_len=160)
            if any(k in ln for k in ("점심", "메뉴", "국밥", "곰탕", "저녁", "맛집")):
                return ln
    return ""


def build_moment_summary_ko(*, intent: str, cards: list[dict]) -> str:
    if intent == "meal":
        meal = first_meal_summary_line(cards)
        if meal:
            return meal
    parts = [
        sanitize_consumer_fragment(c["body_ko"].split("\n")[0], max_len=120)
        for c in cards[:2]
        if c.get("body_ko")
    ]
    parts = [p for p in parts if p and not _OPS_SKIP.search(p)]
    summary = " · ".join(parts)
    return summary or "오늘 가이드에서 순간 성찰만 비춥니다."


def build_consumer_hero_body(
    *,
    fusion_line: str,
    myeongni_first: str,
    lifestyle_lines: list[str],
    calendar_kst: str,
    city: str,
) -> str:
    parts: list[str] = []
    weather = next((ln for ln in lifestyle_lines if "날씨" in ln), "")
    if weather:
        parts.append(sanitize_consumer_fragment(weather, max_len=80))

    calm = ""
    for raw in (myeongni_first, fusion_line):
        for seg in str(raw or "").split("·"):
            seg = sanitize_consumer_fragment(seg, max_len=120)
            if len(seg) < 12 or _OPS_SKIP.search(seg):
                continue
            if "오늘 한 줄" in seg:
                seg = seg.split(":", 1)[-1].strip() or seg
            calm = seg
            break
        if calm:
            break

    if fusion_line and "→" in fusion_line:
        tail = sanitize_consumer_fragment(fusion_line.split("→")[-1], max_len=120)
        if tail and not _OPS_SKIP.search(tail):
            parts.append(tail)
    elif calm:
        parts.append(calm)

    if not parts:
        return f"오늘의 마음을 가볍게 돌아보는 날 · {calendar_kst}"
    body = " · ".join(parts[:2])
    if city and city not in body:
        return body[:240]
    return body[:240]
