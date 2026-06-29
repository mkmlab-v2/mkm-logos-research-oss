from scripts.core.lexicon_function_word_denylist_v1 import (
    FUNCTION_WORD_DENYLIST,
    filter_lexicon_hits,
)


def test_filter_removes_function_words():
    hits = {"the", "bible", "and", "체질"}
    out, n = filter_lexicon_hits(hits, exclude_function_words=True)
    assert "the" not in out
    assert "and" not in out
    assert "bible" in out
    assert n == 2


def test_denylist_frozen_nonempty():
    assert "the" in FUNCTION_WORD_DENYLIST
