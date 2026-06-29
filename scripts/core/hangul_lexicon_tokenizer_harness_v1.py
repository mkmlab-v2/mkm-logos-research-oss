# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.6, M:0.45}
# Balance: 85
# Purpose: B-track Hangul token expansion for lexicon lookup harness ([HYPO], opt-in).
# Keywords: hangul, tokenizer, lexicon, harness
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_HANGUL_SYLLABLE_RE = re.compile(r"[\uac00-\ud7a3]")
_HANGUL_RUN_RE = re.compile(r"[\uac00-\ud7a3]+")
_ZONE_C_HANGUL = _ROOT / "codebook" / "shards" / "zone_c_hangul.json"

# Longest-first particle / ending strips (research heuristic, not morphological analyzer).
_PARTICLE_SUFFIXES = tuple(
    sorted(
        (
            "에게는",
            "에게",
            "으로",
            "에서",
            "이고",
            "부터",
            "까지",
            "처럼",
            "보다",
            "이라",
            "이며",
            "이며",
            "에는",
            "에는",
            "과",
            "와",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "에",
            "의",
            "로",
            "도",
            "만",
            "때",
        ),
        key=len,
        reverse=True,
    )
)


def hangul_syllable_tokens(raw: str) -> set[str]:
    return set(_HANGUL_SYLLABLE_RE.findall(raw))


def hangul_syllable_bigram_tokens(raw: str) -> set[str]:
    out: set[str] = set()
    for run in _HANGUL_RUN_RE.findall(raw):
        if len(run) < 2:
            continue
        for i in range(len(run) - 1):
            out.add(run[i : i + 2])
    return out


def hangul_stem_candidates(raw: str) -> set[str]:
    """Strip common trailing particles from Unicode word tokens that contain Hangul."""
    import re as _re

    out: set[str] = set()
    for tok in _re.findall(r"\w+", raw, flags=_re.UNICODE):
        if not _HANGUL_SYLLABLE_RE.search(tok):
            continue
        base = tok
        changed = True
        while changed and len(base) >= 2:
            changed = False
            for suf in _PARTICLE_SUFFIXES:
                if base.endswith(suf) and len(base) > len(suf):
                    base = base[: -len(suf)]
                    changed = True
                    out.add(base)
                    break
        out.add(tok)
        if len(base) >= 2:
            out.add(base)
    return out


def hangul_harness_token_set(raw: str, *, profile: str = "v1") -> set[str]:
    """Union token candidates for harness lookup (lowercased ASCII only; Hangul kept as-is)."""
    if profile != "v1":
        raise ValueError(f"unsupported harness profile: {profile}")
    toks: set[str] = set()
    toks |= hangul_syllable_tokens(raw)
    toks |= hangul_syllable_bigram_tokens(raw)
    toks |= hangul_stem_candidates(raw)
    normalized: set[str] = set()
    for t in toks:
        if not t:
            continue
        if t.isascii():
            normalized.add(t.lower())
        else:
            normalized.add(t)
    return normalized


@lru_cache(maxsize=1)
def zone_c_hangul_overlay_forms() -> frozenset[str]:
    """B-track research overlay from zone_c_hangul shard (not 41k production SSOT)."""
    if not _ZONE_C_HANGUL.is_file():
        return frozenset()
    doc = json.loads(_ZONE_C_HANGUL.read_text(encoding="utf-8"))
    forms: set[str] = set()
    for key in ("must_keep_hard_terms", "must_keep_soft_terms", "routing_keywords"):
        for term in doc.get(key) or []:
            if isinstance(term, str) and term.strip():
                t = term.strip()
                forms.add(t.lower() if t.isascii() else t)
    return frozenset(forms)


def harness_lookup_tokens(
    raw: str,
    *,
    use_hangul_harness: bool = False,
    use_zone_c_overlay: bool = False,
    unicode_word_toks: set[str] | None = None,
) -> tuple[set[str], dict[str, Any]]:
    import re as _re

    base = unicode_word_toks if unicode_word_toks is not None else {
        t.lower() if t.isascii() else t
        for t in _re.findall(r"\w+", raw, flags=_re.UNICODE)
    }
    toks = set(base)
    meta: dict[str, Any] = {
        "unicode_word_token_count": len(base),
        "hangul_harness_enabled": use_hangul_harness,
        "zone_c_overlay_enabled": use_zone_c_overlay,
    }
    if use_hangul_harness:
        h = hangul_harness_token_set(raw)
        toks |= h
        meta["hangul_harness_token_count"] = len(h)
    if use_zone_c_overlay:
        toks |= set(zone_c_hangul_overlay_forms())
        meta["zone_c_overlay_form_count"] = len(zone_c_hangul_overlay_forms())
    meta["combined_token_count"] = len(toks)
    return toks, meta
