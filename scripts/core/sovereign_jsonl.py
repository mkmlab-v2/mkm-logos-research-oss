# -*- coding: utf-8 -*-
"""Sovereign JSONL: central iterator for line-delimited JSON with Track A/B bulkhead.

Track A (ops-shaped) loaders should use ``track_context=\"A\"`` so rows tagged
``source_track: B`` raise before downstream processing. Track B / research
pipelines use ``track_context=\"B\"`` (no row-level guard).

Does not intercept raw ``open()``; callers must opt in by importing this module.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from scripts.core.track_source_guard import assert_track_a_json_row_allowed

TrackContext = Literal["A", "B"]


def iter_jsonl_dict_rows(
    path: Path | str,
    *,
    track_context: TrackContext = "A",
    encoding: str = "utf-8",
) -> Iterator[dict[str, Any]]:
    """Yield JSON objects from a UTF-8 JSONL file (one JSON object per non-empty line).

    Non-dict JSON values are skipped. For ``track_context==\"A\"``, each dict row is
    validated with ``assert_track_a_json_row_allowed`` (rejects ``source_track: B``).
    """
    p = Path(path)
    with p.open("r", encoding=encoding) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj: Any = json.loads(line)
            if not isinstance(obj, dict):
                continue
            if track_context == "A":
                assert_track_a_json_row_allowed(obj, context=f"{p.as_posix()}:{lineno}")
            yield obj
