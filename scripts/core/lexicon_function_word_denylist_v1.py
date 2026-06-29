"""English function-word denylist for lexicon→must_keep bridge (B-track, opt-in)."""
from __future__ import annotations

# Align with scripts/build_lexicon_lookup_exception_audit_v1.py
FUNCTION_WORD_DENYLIST = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "can",
        "for",
        "from",
        "in",
        "is",
        "it",
        "not",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "to",
        "while",
        "with",
    }
)


def filter_lexicon_hits(hits: set[str], *, exclude_function_words: bool) -> tuple[set[str], int]:
    if not exclude_function_words:
        return set(hits), 0
    removed = {h for h in hits if h in FUNCTION_WORD_DENYLIST}
    return {h for h in hits if h not in FUNCTION_WORD_DENYLIST}, len(removed)
