"""Deterministic morphhb_wlc_multi resolution helpers."""

from __future__ import annotations

from scripts.resolve_morphhb_multi_deterministic import _pick_deterministic


def test_pick_strong_intersection_unique():
    cands = [
        {"lemma": "853", "morph": "A", "strongs_hints": ["H853"]},
        {"lemma": "854", "morph": "B", "strongs_hints": ["H854"]},
    ]
    ch, rule = _pick_deterministic(cands, ["H854"])
    assert ch["lemma"] == "854"
    assert rule == "strong_intersection_unique"


def test_pick_strong_intersection_lexicographic_tie():
    cands = [
        {"lemma": "854", "morph": "B", "strongs_hints": ["H854"]},
        {"lemma": "853", "morph": "A", "strongs_hints": ["H853"]},
    ]
    ch, rule = _pick_deterministic(cands, ["H853", "H854"])
    assert ch["lemma"] == "853"
    assert rule == "strong_intersection_lexicographic"


def test_pick_lexicographic_when_no_strong_overlap():
    cands = [
        {"lemma": "2", "morph": "x", "strongs_hints": ["H2"]},
        {"lemma": "1", "morph": "y", "strongs_hints": ["H1"]},
    ]
    ch, rule = _pick_deterministic(cands, [])
    assert ch["lemma"] == "1"
    assert rule == "lexicographic_all_candidates"
