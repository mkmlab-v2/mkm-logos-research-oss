"""Gematria lexicon router helpers — lookup sidecar only [HYPO], B-track."""

from __future__ import annotations

import re
from typing import Any

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

GNOSIS_STRONGS_EDGE = "GNOSIS_STRONGS_CONTAIN"
_STRONGS_RE = re.compile(r"^[gh]\d+$", re.IGNORECASE)

_SCORING_STOP_TOKENS = frozenset(
    {
        "때",
        "성경",
        "경로",
        "어디",
        "무엇",
    }
)


def _token_in_hay(token: str, hay: str) -> bool:
    if not token or not hay:
        return False
    return token.lower() in hay.lower()


def _normalize_strongs(raw: str) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return ""
    if s.isdigit():
        return f"H{s}"
    return s


def _canon_verse_id(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    c = canonical_verse_ref(s)
    if c and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
        return c
    return c


def _gloss_tokens(gloss: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,;:]+", gloss.lower()):
        for word in re.split(r"\s+", part.strip()):
            if len(word) >= 2:
                out.append(word)
    return out


def _row_match_tokens(
    row: dict[str, Any],
    query_tokens: list[str],
) -> tuple[list[str], list[str]]:
    gloss = str(row.get("gloss") or "")
    translit = str(row.get("transliteration") or "")
    strongs = _normalize_strongs(str(row.get("strongs") or ""))
    gloss_hay = gloss.lower()
    translit_hay = translit.lower().replace(".", " ")
    gloss_words = set(_gloss_tokens(gloss))

    matched: list[str] = []
    fields: list[str] = []
    for t in query_tokens:
        if t in _SCORING_STOP_TOKENS or len(t) < 2:
            continue
        hit = False
        if strongs and _STRONGS_RE.match(t) and t.upper() == strongs:
            if "strongs" not in fields:
                fields.append("strongs")
            hit = True
        if not hit and _token_in_hay(t, gloss_hay):
            if "gloss" not in fields:
                fields.append("gloss")
            hit = True
        if not hit and _token_in_hay(t, translit_hay):
            if "transliteration" not in fields:
                fields.append("transliteration")
            hit = True
        if not hit and t in gloss_words:
            if "gloss" not in fields:
                fields.append("gloss")
            hit = True
        if hit:
            matched.append(t)
    return matched, fields


def match_lexicon_hits(
    query_tokens: list[str],
    rows: list[dict[str, Any]],
    *,
    max_hits: int = 15,
) -> list[dict[str, Any]]:
    """Return lexicon rows whose gloss/transliteration/strongs overlap query tokens."""
    if not query_tokens or not rows:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    seen_strongs: set[str] = set()

    for row in rows:
        if str(row.get("kernel_recipe_id") or "") != "gematria_bridge_v1":
            continue
        matched, fields = _row_match_tokens(row, query_tokens)
        if not matched:
            continue
        strongs = _normalize_strongs(str(row.get("strongs") or ""))
        if strongs and strongs in seen_strongs:
            continue
        if strongs:
            seen_strongs.add(strongs)
        hit = {
            "entry_id": row.get("entry_id"),
            "strongs": strongs or row.get("strongs"),
            "language": row.get("language"),
            "lemma": row.get("lemma"),
            "gloss": row.get("gloss"),
            "transliteration": row.get("transliteration"),
            "match_tokens": matched,
            "match_fields": fields,
            "match_score": len(matched),
            "vector_4d": row.get("vector_4d"),
            "kernel_recipe_id": row.get("kernel_recipe_id"),
            "gematria": row.get("gematria"),
            "lookup_only": row.get("lookup_only", True),
            "hypothesis_tier": row.get("hypothesis_tier", "B"),
        }
        scored.append((len(matched), hit))

    scored.sort(key=lambda x: (x[0], str(x[1].get("strongs") or "")), reverse=True)
    return [hit for _score, hit in scored[:max_hits]]


def strongs_verse_ids_from_lemma(
    strongs_set: set[str] | frozenset[str],
    lemma_rows: list[dict[str, Any]],
    *,
    max_verses: int = 20,
) -> list[str]:
    """Map Strong numbers to verse ids via GNOSIS_STRONGS_CONTAIN lemma edges."""
    if not strongs_set or not lemma_rows:
        return []

    normalized = {_normalize_strongs(s) for s in strongs_set if s}
    normalized.discard("")

    out: list[str] = []
    seen: set[str] = set()
    for row in lemma_rows:
        if str(row.get("edge_type") or "") != GNOSIS_STRONGS_EDGE:
            continue
        sn = _normalize_strongs(str(row.get("strongs_number") or ""))
        if not sn or sn not in normalized:
            continue
        dst = _canon_verse_id(str(row.get("dst_node_id") or ""))
        if dst and dst not in seen:
            seen.add(dst)
            out.append(dst)
            if len(out) >= max_verses:
                break
    return out
