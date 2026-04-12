# -*- coding: utf-8 -*-
"""Track A/B source tagging guard (scripts/core/track_source_guard.py)."""

from __future__ import annotations

import pytest

from scripts.core.track_source_guard import (
    assert_track_a_json_row_allowed,
    is_track_b_provenance,
    is_track_b_record,
    normalized_source_track,
)


def test_normalized_source_track() -> None:
    assert normalized_source_track("B") == "B"
    assert normalized_source_track("track_b") == "B"
    assert normalized_source_track("A") == "A"
    assert normalized_source_track("enterprise") == "A"
    assert normalized_source_track(None) is None
    assert normalized_source_track("unknown") is None


def test_is_track_b_provenance() -> None:
    assert is_track_b_provenance({"source_track": "B"}) is True
    assert is_track_b_provenance({"source_track": "research"}) is True
    assert is_track_b_provenance({"source_track": "A"}) is False
    assert is_track_b_provenance({}) is False


def test_assert_track_a_rejects_b() -> None:
    with pytest.raises(ValueError, match="Track B row"):
        assert_track_a_json_row_allowed({"source_track": "B", "x": 1}, context="unit")
    assert_track_a_json_row_allowed({"source_track": "A"})
    assert_track_a_json_row_allowed({})


def test_is_track_b_record_top_level() -> None:
    assert is_track_b_record({"source_track": "b"}) is True
    assert is_track_b_record({"foo": 1}) is False
