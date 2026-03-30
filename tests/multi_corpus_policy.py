# @MKM12-METADATA
# Type: Logic
# Purpose: §4 parallel-corpus Fact-Lock — canonical default guard for verse-like records.
"""Multi-corpus isolation helpers (CONSTITUTION §4).

Core A-track lists may omit ``corpus_type`` (implicit canonical). Satellite records must
set ``corpus_type``; unknown/empty on an explicitly tagged non-canonical row is still
non-canonical for the default guard.

Tracked under ``tests/`` so CI clones include this module (``tools/`` may be locally excluded).
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator, Mapping

_CANONICAL = frozenset({"", "canonical"})


def corpus_type_of(record: Mapping[str, Any]) -> str:
    """Return normalized corpus_type; missing field defaults to ``canonical``."""
    raw = record.get("corpus_type")
    if raw is None:
        return "canonical"
    return str(raw).strip().lower() or "canonical"


def is_canonical_for_default_guard(record: Mapping[str, Any]) -> bool:
    """True iff default canonical-only sweep should include this record."""
    return corpus_type_of(record) in _CANONICAL


def iter_canonical_only(
    verses: Iterable[Mapping[str, Any]],
    *,
    include_satellites: bool = False,
) -> Iterator[Mapping[str, Any]]:
    """Yield verses under §4 default guard (canonical-only unless satellites requested)."""
    for v in verses:
        if include_satellites or is_canonical_for_default_guard(v):
            yield v


def cross_ref_artifact_name(stem: str) -> str:
    """Return filename for non-invasive cross-corpus reports (does not write files)."""
    safe = stem.replace("/", "_").replace("\\", "_").strip() or "report"
    return f"CROSS_REF_{safe}.json"
