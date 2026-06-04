"""[HYPO] Next-Gen latent codec helpers (B-track · not neural E2E)."""
from __future__ import annotations

import re
import zlib
from typing import Iterable

WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]+")
_MUST_KEEP_DEFAULT = frozenset({"사상의학", "체질", "sasang", "myeongri", "bible"})


def norm_words(text: str) -> set[str]:
    return set(WORD_RE.findall(text.lower()))


def jaccard_text(a: str, b: str) -> float:
    sa, sb = norm_words(a), norm_words(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def token_salience(tok: str, must_keep: Iterable[str] = _MUST_KEEP_DEFAULT) -> float:
    low = tok.lower()
    score = len(tok) ** 0.5
    for mk in must_keep:
        m = mk.lower()
        if m in low or low in m:
            score += 50.0
    return score


def latent_salience_reconstruct(
    raw: str,
    keep_ratio: float,
    *,
    must_keep: Iterable[str] = _MUST_KEEP_DEFAULT,
) -> tuple[str, str]:
    """Keep top-salience token positions until keep_ratio of instances; preserve order."""
    tokens = WORD_RE.findall(raw)
    if not tokens:
        return "", ""
    kr = max(0.05, min(0.98, keep_ratio))
    keep_n = max(1, int(round(len(tokens) * kr)))
    ranked = sorted(
        range(len(tokens)),
        key=lambda i: (token_salience(tokens[i], must_keep), len(tokens[i])),
        reverse=True,
    )
    keep_idx = set(ranked[:keep_n])
    ordered = [tokens[i] for i in range(len(tokens)) if i in keep_idx]
    compressed = " ".join(ordered)
    return compressed, compressed


def latent_crc_stub_reconstruct(raw: str, keep_percent: int) -> tuple[str, str]:
    """Legacy P2 CRC stub (for A/B vs salience PoC)."""
    tokens = WORD_RE.findall(raw)
    if not tokens:
        return "", ""
    kept: list[str] = []
    for tok in tokens:
        bucket = zlib.crc32(tok.lower().encode("utf-8")) % 100
        if bucket < keep_percent:
            kept.append(tok)
    if not kept:
        kept = [tokens[0]]
    compressed = " ".join(kept)
    return compressed, compressed
