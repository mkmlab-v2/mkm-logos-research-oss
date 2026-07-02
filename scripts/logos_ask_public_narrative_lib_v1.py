"""Public S4 narrative heuristics — aligned with logosInquiryAskDisplayV1.ts (display layer)."""
from __future__ import annotations

import re
from typing import Any

DOGMA_RE = re.compile(
    r"(?<!금지\s)(?<!없음\s)(반드시|확실히\s*말|투자\s*시그널|매수|매도|적그리스도는\s*바로|666은\s*반드시)",
    re.I,
)
SCRIPTURE_QUOTE_RE = re.compile(
    r"(?:“|\"|「|\u201c)(?:[^”\"」\n]|\\\"){0,500}(?:”|\"|」|\u201d)"
    r'|"(?:[^"\n]|\\"){0,500}"',
)
VERSE_CITATION_SNIPPET_RE = re.compile(
    r"[^.!?\n]{0,160}?(?:\([A-Za-z][A-Za-z0-9]*\.\d+\.\d+\)|[A-Za-z][A-Za-z0-9]*\.\d+\.\d+)",
)
SCRIPTURE_EXPOSITION_CLAUSE_RE = re.compile(
    r"[^.!?\n]*(?:"
    r"(?:\([A-Za-z][A-Za-z0-9]*\.\d+\.\d+\)|[A-Za-z][A-Za-z0-9]*\.\d+\.\d+|\d+\s*장\s*\d+\s*절)"
    r"[^.!?\n]*(?:반드시|확실히\s*말|적그리스도는\s*바로|666은\s*반드시)"
    r"|(?:반드시|확실히\s*말|적그리스도는\s*바로|666은\s*반드시)"
    r"[^.!?\n]*(?:\([A-Za-z][A-Za-z0-9]*\.\d+\.\d+\)|[A-Za-z][A-Za-z0-9]*\.\d+\.\d+|\d+\s*장\s*\d+\s*절)"
    r")[^.!?\n]*[.!?…]?",
    re.I,
)
GUARD_RESPONSE_RE = re.compile(
    r"topic_mismatch|직접\s*대응하지\s*않습니다|재질의를\s*권합니다|억지\s*연결\s*없이",
    re.I,
)
TAG_RE = re.compile(r"\[HYPO\]|\[NON_GATING\]|research_only|send_gate", re.I)
SPLIT_RE = re.compile(r"(?:^|\n|\s)---(?:\s|\n)|###\s*Reading pack", re.I)
GEMATRIA_OR_META_LINE_RE = re.compile(
    r"combined_sum|vector_4d|hub_score|state16|Gematria_Pin|topology pin|mispar_|"
    r"^\*\*(Query|Pack|Governance|query_id|utterance_class):",
    re.I,
)
STUDIO_BOILERPLATE_RE = re.compile(r"디지털\s*환경에서\s*정보의\s*진실성", re.I)


def strip_public_research_tags(text: str) -> str:
    s = text or ""
    s = re.sub(r"\[HYPO\]\s*", "", s, flags=re.I)
    s = re.sub(r"\[NON_GATING\]\s*", "", s, flags=re.I)
    s = re.sub(r"\bresearch_only\b", "", s, flags=re.I)
    s = re.sub(r"\bsend_gate\s*:\s*\w+", "", s, flags=re.I)
    s = re.sub(r"디지털\s*환경에서\s*정보의\s*진실성[^.!?…]*[.!?…]?", "", s, flags=re.I)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def split_s4_public_body(body: str) -> tuple[str, str]:
    raw = (body or "").strip()
    if not raw:
        return "", ""
    parts = SPLIT_RE.split(raw, maxsplit=1)
    narrative = strip_public_research_tags((parts[0] if parts else "").strip())
    reading = strip_public_research_tags(parts[1].strip()) if len(parts) > 1 else ""
    if reading and STUDIO_BOILERPLATE_RE.search(reading):
        reading = ""
    return narrative, reading


def is_gematria_or_meta_line(line: str) -> bool:
    t = (line or "").strip()
    if not t:
        return True
    return bool(GEMATRIA_OR_META_LINE_RE.search(t)) or bool(STUDIO_BOILERPLATE_RE.search(t))


def format_public_narrative_paragraphs(body: str) -> list[str]:
    narrative, _ = split_s4_public_body(body)
    source = narrative or strip_public_research_tags(body)
    if not source:
        return []

    blocks = [p.strip() for p in re.split(r"\n{2,}|\n(?=###\s+)", source) if p.strip()]
    paragraphs: list[str] = []

    for block in blocks:
        if is_gematria_or_meta_line(block):
            continue
        text = block
        if text.startswith("###"):
            lines = [ln.strip() for ln in re.split(r"\n+", text) if ln.strip()]
            title = re.sub(r"^###\s*\d*\.?\s*", "", lines[0] if lines else "").strip()
            body_text = " ".join(lines[1:]).strip()
            text = " — ".join([x for x in (title, body_text) if x])
        else:
            text = re.sub(r"\n+", " ", text)
            text = re.sub(r"\s{2,}", " ", text).strip()
        if len(text) > 20 and not is_gematria_or_meta_line(text):
            paragraphs.append(text)

    if not paragraphs and len(source) > 20:
        single = re.sub(r"\n+", " ", source)
        single = re.sub(r"\s{2,}", " ", single).strip()
        if not is_gematria_or_meta_line(single):
            paragraphs.append(single)
    return paragraphs


def meets_public_narrative_quality(
    body: str,
    *,
    min_chars: int = 120,
    min_paragraphs: int = 2,
) -> dict[str, object]:
    paragraphs = format_public_narrative_paragraphs(body)
    _, reading = split_s4_public_body(body)
    intro = (reading.split("\n###")[0] if reading else "").strip()
    intro_line = re.sub(r"\s{2,}", " ", intro)[:220]
    public_text = "\n".join([*paragraphs, intro_line]).strip()
    char_count = len(public_text)
    paragraph_count = len(paragraphs)
    return {
        "narrative_ok": char_count >= min_chars and paragraph_count >= min_paragraphs,
        "char_count": char_count,
        "paragraph_count": paragraph_count,
    }


def strip_scripture_quotes_for_dogma(text: str) -> str:
    scrubbed = text or ""
    scrubbed = SCRIPTURE_QUOTE_RE.sub(" ", scrubbed)
    scrubbed = VERSE_CITATION_SNIPPET_RE.sub(" ", scrubbed)
    scrubbed = SCRIPTURE_EXPOSITION_CLAUSE_RE.sub(" ", scrubbed)
    return scrubbed


def dogma_violation(text: str) -> bool:
    if re.search(r"단정\s*금지|확정\s*없음|단정\s*없음|해석\s*확정\s*없", text, re.I):
        return False
    scrubbed = strip_scripture_quotes_for_dogma(text)
    return bool(DOGMA_RE.search(scrubbed))


def has_anchor(text: str, refs: list[str]) -> bool:
    t = re.sub(r"\s", "", text).lower()
    for ref in refs:
        r = re.sub(r"\s", "", str(ref)).lower()
        book = r.split(".")[0] if "." in r else r
        if r in t or book.lower() in t:
            return True
    return False


def score_logos_ask_row(
    item: dict[str, Any],
    body_raw: str,
    preset_id: str | None,
    query_mode: str | None,
) -> dict[str, Any]:
    narrative, _ = split_s4_public_body(body_raw)
    public_text = strip_public_research_tags(narrative or body_raw)
    is_guard = "topic_mismatch_guard" in str(query_mode or "") or bool(GUARD_RESPONSE_RE.search(public_text))
    forbidden = list(item.get("forbidden_preset_ids") or [])
    preset_bad = bool(preset_id and preset_id in forbidden)
    anchor_ok = has_anchor(public_text, list(item.get("gold_primary_refs") or []))
    wrong_pack = False
    qid = str(item.get("id") or "")
    if qid == "live_rev21_longtail" and re.search(r"666·적그리스도|짐승의\s*수", public_text):
        wrong_pack = True
    narrative_quality = meets_public_narrative_quality(body_raw)
    narrative_ok = bool(narrative_quality.get("narrative_ok"))
    tags_ok = not TAG_RE.search(public_text)
    dogma_ok = not dogma_violation(public_text)
    guard_only_fail = bool(item.get("reject_guard_only")) and is_guard
    quality_pass = (
        not preset_bad
        and not guard_only_fail
        and not wrong_pack
        and anchor_ok
        and narrative_ok
        and tags_ok
        and dogma_ok
    )
    return {
        "id": item.get("id"),
        "query_ko": item.get("query_ko"),
        "quality_tier": item.get("quality_tier"),
        "preset_id": preset_id,
        "query_mode": query_mode,
        "topic_mismatch_guard": is_guard,
        "public_preview_200": public_text[:200],
        "narrative_paragraph_count": narrative_quality.get("paragraph_count"),
        "checks": {
            "preset_ok": not preset_bad,
            "anchor_ok": anchor_ok,
            "routing_ok": not wrong_pack,
            "narrative_ok": narrative_ok,
            "public_tags_ok": tags_ok,
            "dogma_ok": dogma_ok,
            "guard_only_ok": not guard_only_fail,
        },
        "quality_pass": quality_pass,
    }
