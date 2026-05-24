"""KO tokenization strategies for inter-agent lexicon experiments (research_only)."""

from __future__ import annotations

import re
from typing import Literal

TokenizationMode = Literal["word", "hangul_syllable", "hangul_char"]

_HANGUL_SYLLABLE_RE = re.compile(r"[\uAC00-\uD7A3]+")
_LATIN_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


def is_hangul_char(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    return 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F


def tokenize(text: str, mode: TokenizationMode = "word") -> list[str]:
    if mode == "word":
        from scripts.core.master_codebook_lexicon_v1_bridge import unicode_word_tokens

        return sorted(unicode_word_tokens(text))

    tokens: list[str] = []
    if mode == "hangul_syllable":
        for block in _HANGUL_SYLLABLE_RE.findall(text):
            tokens.extend(list(block))
        for w in _LATIN_WORD_RE.findall(text):
            tokens.append(w.lower())
        return tokens

    if mode == "hangul_char":
        for ch in text:
            if is_hangul_char(ch):
                tokens.append(ch)
        for w in _LATIN_WORD_RE.findall(text):
            tokens.append(w.lower())
        return tokens

    raise ValueError(f"unknown_mode:{mode}")
