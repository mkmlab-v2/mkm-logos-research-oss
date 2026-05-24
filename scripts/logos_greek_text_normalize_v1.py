#!/usr/bin/env python3
"""Normalize Greek manuscript text for lexical cross-source comparison (B-track)."""

from __future__ import annotations

import re
import unicodedata

_GREEK_PUNCT_RE = re.compile(r"[\s·.,;:!?\"''""«»()\[\]{}—–\-]+")


def strip_greek_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def normalize_greek_lexical(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace/punctuation for equality checks."""
    t = strip_greek_accents(text or "")
    t = t.lower()
    t = _GREEK_PUNCT_RE.sub(" ", t)
    return " ".join(t.split())
