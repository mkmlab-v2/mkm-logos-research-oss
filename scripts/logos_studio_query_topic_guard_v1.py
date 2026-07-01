#!/usr/bin/env python3
"""Query-topic vs conflict/path relevance guard for Logos Studio Ask (B-track).

Blocks cross-chapter LLM hallucination (e.g. Eve/rib question answered from Gen 6 schools).
"""
from __future__ import annotations

import re
from typing import Any

GEN6_CONFLICT_IDS = frozenset(
    {
        "MKM_CONCEPT_SONS_OF_GOD",
        "MKM_CONCEPT_NEPHILIM",
        "Sons_of_God_Theological_Interpretation",
    }
)

EVE_CREATION_MARKERS = (
    "하와",
    "갈비",
    "갈비뼈",
    "측",
    "돕는 배필",
    "돕는 자",
    "eve",
    "rib",
    "tsela",
    "woman from man",
    "side of adam",
)

GEN6_QUERY_MARKERS = (
    "네피림",
    "nephilim",
    "하나님의 아들",
    "sons of god",
    "benei",
    "watcher",
    "감시자",
    "창세기 6",
    "genesis 6",
    "gen 6",
    "gen.6",
)

VERSE_REF_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\.(\d+)\.(\d+)\b")

ANTICHRIST_666_MARKERS = (
    "666",
    "적그리스도",
    "안티크라이스트",
    "antichrist",
    "계시록 13",
    "계시록13",
    "rev 13",
    "rev.13",
    "요한계시록",
    "짐승의 숫자",
    "마귀의 숫자",
    "beast number",
    "mark of the beast",
)

JOB_SUFFERING_PRESET_IDS = frozenset({"job_job_suffering_reason", "job_existential_suffering"})
APOCALYPTIC_TOPIC_BOOKS = frozenset({"Rev", "1John", "2Thess"})
SUFFERING_STUB_BOOKS = frozenset({"Job", "Ps", "Jer"})

from scripts.build_logos_golden_200_anchor_registry_v1 import SEED_ENTRIES


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def query_flags(query: str) -> dict[str, bool]:
    q = _norm(query)
    eve = any(m in q for m in EVE_CREATION_MARKERS) or ("아담" in q and ("뼈" in q or "측" in q))
    gen6 = any(m in q for m in GEN6_QUERY_MARKERS)
    passion_crown = any(
        m in q for m in ("가시면류관", "면류관", "가시 관", "crown of thorns")
    ) and any(
        m in q
        for m in (
            "예수",
            "그리스도",
            "십자가",
            "수난",
            "passion",
            "마태",
            "마가",
            "요한",
        )
    )
    antichrist_666 = any(m in q for m in ANTICHRIST_666_MARKERS)
    return {
        "eve_creation": eve and not gen6,
        "gen6": gen6,
        "passion_crown": passion_crown,
        "antichrist_666": antichrist_666,
    }


def _verse_chapters_from_text(text: str) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for book, ch, _ in VERSE_REF_RE.findall(text or ""):
        out.setdefault(book, set()).add(int(ch))
    return out


def _chapters_from_path(path: dict[str, Any]) -> dict[str, set[int]]:
    parts: list[str] = []
    for ref in path.get("verse_refs") or []:
        parts.append(str(ref))
    for step in path.get("steps") or []:
        parts.append(str(step))
    return _verse_chapters_from_text(" ".join(parts))


def _chapters_from_conflict(conflict: dict[str, Any] | None) -> dict[str, set[int]]:
    if not conflict:
        return {}
    parts: list[str] = []
    for group in conflict.get("groups") or []:
        if not isinstance(group, dict):
            continue
        parts.append(str(group.get("conflict_group_id") or ""))
        parts.append(str(group.get("lexicon_base") or ""))
        for school in group.get("schools") or []:
            if not isinstance(school, dict):
                continue
            for vr in school.get("verse_refs") or []:
                parts.append(str(vr))
    return _verse_chapters_from_text(" ".join(parts))


def primary_conflict_group_id(conflict: dict[str, Any] | None) -> str | None:
    if not conflict:
        return None
    groups = conflict.get("groups") or []
    if not groups:
        return None
    first = groups[0]
    if isinstance(first, dict):
        return str(first.get("conflict_group_id") or "") or None
    return None


def _books_from_chapters(chapters: dict[str, set[int]]) -> set[str]:
    return set(chapters.keys())


def _match_registry_hub(query: str) -> dict[str, Any] | None:
    q = _norm(query)
    best: dict[str, Any] | None = None
    best_score = 0
    for entry in SEED_ENTRIES:
        score = 0
        for marker in entry.get("query_markers_ko") or []:
            m = _norm(marker)
            if len(m) >= 2 and m in q:
                score += 2
        if entry.get("hub_id") == "gen2_eve_creation":
            if any(x in q for x in ("네피림", "nephilim", "genesis 6", "gen 6")):
                score = 0
        if entry.get("hub_id") == "passion_crown":
            if not any(
                x in q
                for x in ("예수", "그리스도", "십자가", "수난", "passion", "마태", "마가", "요한")
            ):
                score = max(0, score - 1)
        if score > best_score:
            best_score = score
            best = entry
    return best if best_score >= 2 else None


def _detect_registry_hub_mismatch(
    query: str,
    hub: dict[str, Any],
    *,
    conflict: dict[str, Any] | None,
    path: dict[str, Any] | None,
    preset_id: str | None,
) -> dict[str, Any] | None:
    path_ch = _chapters_from_path(path or {})
    conflict_ch = _chapters_from_conflict(conflict)
    path_books = _books_from_chapters(path_ch)
    conflict_books = _books_from_chapters(conflict_ch)
    evidence_books = path_books | conflict_books

    blocked_presets = set(hub.get("blocked_preset_ids") or [])
    if preset_id and preset_id in blocked_presets:
        expected = set(hub.get("expected_books") or [])
        if expected and not (evidence_books & expected):
            return {
                "code": f"{hub['hub_id']}_vs_blocked_preset",
                "expected_anchor_verses": list(hub.get("primary_verse_refs") or [])[:8],
                "hint_ko": (
                    f"질문은 {hub['hub_id']} Hub 맥락인데 차단된 stub 프리셋({preset_id})이 선택되었습니다."
                ),
            }

    expected_books = set(hub.get("expected_books") or [])
    blocked_stub = set(hub.get("blocked_stub_books") or [])
    if expected_books and evidence_books:
        has_expected = bool(evidence_books & expected_books)
        stub_only = bool(blocked_stub) and evidence_books.issubset(blocked_stub | {"Heb", "Dan"})
        if not has_expected and stub_only:
            return {
                "code": f"{hub['hub_id']}_vs_stub_path",
                "expected_anchor_verses": list(hub.get("primary_verse_refs") or [])[:8],
                "hint_ko": (
                    f"질문은 {hub['hub_id']} Hub 맥락인데 검색 경로는 stub({', '.join(sorted(evidence_books))})입니다."
                ),
            }

    for rule in hub.get("book_chapter_rules") or []:
        book = str(rule.get("book") or "")
        if not book:
            continue
        chapters = path_ch.get(book, set()) | conflict_ch.get(book, set())
        if not chapters:
            continue
        blocked = set(rule.get("blocked_chapters") or [])
        expected = set(rule.get("expected_chapters") or [])
        blocked_only = bool(blocked) and chapters.issubset(blocked)
        misses_expected = bool(expected) and not (chapters & expected)
        if blocked_only and misses_expected:
            return {
                "code": f"{hub['hub_id']}_vs_chapter_mismatch",
                "expected_anchor_verses": list(hub.get("primary_verse_refs") or [])[:8],
                "hint_ko": (
                    f"질문은 {book} {sorted(expected)}장 맥락인데 검색 증거는 {book} {sorted(chapters)}장입니다."
                ),
            }
    return None


def detect_query_topic_mismatch(
    query: str,
    *,
    conflict: dict[str, Any] | None,
    path: dict[str, Any] | None,
    preset_id: str | None = None,
) -> dict[str, Any] | None:
    """Return mismatch descriptor when query topic and retrieved evidence diverge."""
    flags = query_flags(query)
    path_ch = _chapters_from_path(path or {})
    conflict_ch = _chapters_from_conflict(conflict)
    path_books = _books_from_chapters(path_ch)
    conflict_books = _books_from_chapters(conflict_ch)
    evidence_books = path_books | conflict_books

    if flags.get("antichrist_666"):
        wrong_preset = bool(preset_id and preset_id in JOB_SUFFERING_PRESET_IDS)
        has_apocalyptic = bool(evidence_books & APOCALYPTIC_TOPIC_BOOKS)
        stub_only = bool(evidence_books) and evidence_books.issubset(
            SUFFERING_STUB_BOOKS | {"Heb", "Dan"}
        )
        if (wrong_preset and not has_apocalyptic) or (
            evidence_books and not has_apocalyptic and stub_only
        ):
            return {
                "code": "antichrist_666_vs_suffering_stub",
                "query_flags": flags,
                "path_books": sorted(path_books),
                "expected_anchor_verses": ["Rev.13.18", "1John.2.18", "1John.4.3", "2Thess.2.3"],
                "hint_ko": (
                    "질문은 요한계시록 13장(666)·적그리스도 맥락인데, 검색된 경로는 시편·욥기·예레미야 등 "
                    "고난/신실함 스텁입니다. Rev.13.18 · 1John.2.18 citation lock 앵커로 재질의하세요."
                ),
            }

    if not flags["eve_creation"]:
        hub = _match_registry_hub(query)
        if hub:
            reg_mismatch = _detect_registry_hub_mismatch(
                query,
                hub,
                conflict=conflict,
                path=path,
                preset_id=preset_id,
            )
            if reg_mismatch:
                reg_mismatch["query_flags"] = flags
                return reg_mismatch
        return None

    gid = primary_conflict_group_id(conflict)
    path_ch = _chapters_from_path(path or {})
    conflict_ch = _chapters_from_conflict(conflict)
    gen_chapters = path_ch.get("Gen", set()) | conflict_ch.get("Gen", set())

    gen6_dominated = bool(gen_chapters) and gen_chapters.issubset({6}) and 2 not in gen_chapters
    wrong_group = gid in GEN6_CONFLICT_IDS

    if not wrong_group and not gen6_dominated:
        return None

    return {
        "code": "eve_creation_vs_gen6_evidence",
        "query_flags": flags,
        "primary_conflict_group_id": gid,
        "gen_chapters": sorted(gen_chapters),
        "expected_anchor_verses": ["Gen.2.21", "Gen.2.22", "Gen.2.23", "Gen.2.24"],
        "hint_ko": (
            "질문은 창세기 2장 하와 창조(갈비·측) 맥락인데, 검색된 충돌면·경로는 창세기 6장 학파 자료입니다. "
            "단일 답변이 아닌 연구 격벽입니다 — Gen.2.21-24 citation lock 앵커로 재질의하세요."
        ),
    }


def build_mismatch_answer(query: str, mismatch: dict[str, Any]) -> str:
    code = str(mismatch.get("code") or "")
    anchors = ", ".join(mismatch.get("expected_anchor_verses") or ["Gen.2.21", "Gen.2.22"])
    if code == "antichrist_666_vs_suffering_stub":
        return (
            f"[HYPO] 질문 「{query.strip()}」은 **요한계시록 13장(666)·적그리스도** 맥락입니다.\n\n"
            "현재 검색된 경로는 **시편·욥기·예레미야** 등 고난/신실함 스텁이라 질문과 **직접 대응하지 않습니다**. "
            "LLM·Azure Distill로 억지 연결하지 않습니다 [NON_GATING].\n\n"
            f"연구 앵커: {anchors}.\n"
            "「요한계시록 13장 666」 또는 「적그리스도 요한일서」로 재질의를 권합니다."
        )
    return (
        f"[HYPO] 질문 「{query.strip()}」은 **창세기 2:21-24**(아담의 갈비/측에서 하와 창조) 맥락입니다.\n\n"
        f"현재 검색된 학파 충돌면은 **창세기 6장**(Benei HaElohim·네피림) 자료라 질문과 **직접 대응하지 않습니다**. "
        f"LLM·동적 합성으로 두 장을 억지 연결하지 않습니다 [NON_GATING].\n\n"
        f"연구 앵커: {anchors}. 원어 צֵלָע(tsela)·동등·결합 상징 등 학파 분기는 이 앵커에서 citation lock으로 펼치세요. "
        f"프리셋 `topic_gen_2_anchor` 또는 「창세기 2장 하와 창조」로 재질의를 권합니다."
    )
