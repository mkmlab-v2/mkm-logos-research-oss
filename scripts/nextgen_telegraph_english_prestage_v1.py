"""[HYPO] Telegraph-English style symbolic prestage (B-track; not paper reimplementation)."""
from __future__ import annotations

import re
from typing import Any

_MUST_KEEP = frozenset({"사상의학", "체질", "sasang", "myeongri", "bible", "logos", "명리"})

_FILLER_EN = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "that",
        "this",
        "these",
        "those",
        "of",
        "to",
        "in",
        "for",
        "on",
        "with",
        "as",
        "by",
        "at",
        "from",
        "or",
        "and",
        "but",
        "if",
        "then",
        "than",
        "also",
        "very",
        "just",
        "really",
    }
)

_FILLER_KO = (
    "그리고",
    "하지만",
    "또한",
    "따라서",
    "즉",
    "또",
    "및",
    "등",
    "것은",
    "것이",
    "있는",
    "하는",
    "된다",
    "입니다",
    "습니다",
)


def _protect_terms(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    out = text
    for i, term in enumerate(sorted(_MUST_KEEP, key=len, reverse=True)):
        if term in out:
            key = f"§MKM{i}§"
            placeholders[key] = term
            out = out.replace(term, key)
    return out, placeholders


def _restore_terms(text: str, placeholders: dict[str, str]) -> str:
    out = text
    for key, term in placeholders.items():
        out = out.replace(key, term)
    return out


def telegraph_prestage(text: str) -> tuple[str, dict[str, Any]]:
    """Deterministic symbolic shorten; lossy vs original."""
    protected, placeholders = _protect_terms(text)
    tokens = re.findall(r"[\w§]+|[^\w\s]", protected, flags=re.UNICODE)
    kept: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if tok in placeholders:
            kept.append(tok)
            continue
        if low in _FILLER_EN:
            continue
        if tok in _FILLER_KO:
            continue
        if re.fullmatch(r"\d+", tok):
            kept.append(tok)
            continue
        if len(tok) <= 1 and not tok.isalnum():
            kept.append(tok)
            continue
        if len(tok) >= 2:
            kept.append(tok)
    prestaged = _restore_terms(" ".join(kept), placeholders)
    prestaged = re.sub(r"\s+", " ", prestaged).strip()
    sidecar = {
        "schema": "telegraph_english_prestage_sidecar_v1",
        "original_len": len(text),
        "prestaged_len": len(prestaged),
        "protected_terms": list(placeholders.values()),
    }
    return prestaged, sidecar


def telegraph_char_saving_rate(original: str, prestaged: str) -> float:
    o = max(1, len(original.encode("utf-8")))
    p = len(prestaged.encode("utf-8"))
    return round(1.0 - (p / o), 6)
