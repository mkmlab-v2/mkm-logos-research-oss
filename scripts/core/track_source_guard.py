# -*- coding: utf-8 -*-
"""Track source tagging for A/B bulkhead (Fact-Lock).

JSON/JSONL rows may set ``source_track`` to mark provenance:
- ``A`` — Track A (ops / universal / enterprise-shaped inputs)
- ``B`` — Track B (research / literal / B-track); Track A loaders must reject or strip.

Callers that are not file-based (e.g. dual_regime API) accept an optional
``state_provenance`` mapping with the same field.
"""

from __future__ import annotations

from typing import Any, Mapping

SOURCE_TRACK_FIELD = "source_track"

# Normalized tags treated as Track B for defensive suppression.
_TRACK_B_ALIASES = frozenset(
    {
        "b",
        "track_b",
        "trackb",
        "literal",
        "research",
        "b_track",
        "b-track",
    }
)


def normalized_source_track(value: Any) -> str | None:
    """Return upper single-letter tag ``A`` or ``B``, or None if missing/unknown."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    low = s.lower()
    if low in _TRACK_B_ALIASES or low == "b":
        return "B"
    if low in ("a", "track_a", "tracka", "active", "enterprise", "universal"):
        return "A"
    return None


def is_track_b_provenance(provenance: Mapping[str, Any] | None) -> bool:
    """True if ``provenance`` explicitly marks Track B."""
    if not provenance:
        return False
    tag = normalized_source_track(provenance.get(SOURCE_TRACK_FIELD))
    return tag == "B"


def is_track_b_record(record: Mapping[str, Any]) -> bool:
    """True if top-level ``source_track`` marks Track B."""
    return is_track_b_provenance(record)


def assert_track_a_json_row_allowed(
    record: Mapping[str, Any],
    *,
    context: str = "",
) -> None:
    """Raise ValueError if ``record`` is tagged Track B (Track A loader guard)."""
    if not is_track_b_record(record):
        return
    msg = "Track B row cannot be loaded on Track A path (source_track=B)"
    if context:
        msg = f"{msg}: {context}"
    raise ValueError(msg)
