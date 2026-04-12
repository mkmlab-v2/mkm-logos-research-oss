# -*- coding: utf-8 -*-
"""Sovereign JSONL iterator (scripts/core/sovereign_jsonl.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_track_a_rejects_b_row(tmp_path: Path) -> None:
    from scripts.core.sovereign_jsonl import iter_jsonl_dict_rows

    p = tmp_path / "x.jsonl"
    p.write_text(
        json.dumps({"source_track": "B", "k": 1}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Track B row"):
        list(iter_jsonl_dict_rows(p, track_context="A"))


def test_track_a_allows_a_and_untagged(tmp_path: Path) -> None:
    from scripts.core.sovereign_jsonl import iter_jsonl_dict_rows

    p = tmp_path / "y.jsonl"
    p.write_text(
        json.dumps({"source_track": "A", "x": 1}, ensure_ascii=False)
        + "\n"
        + json.dumps({"plain": 2}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    rows = list(iter_jsonl_dict_rows(p, track_context="A"))
    assert len(rows) == 2
    assert rows[0]["x"] == 1
    assert rows[1]["plain"] == 2


def test_track_b_allows_b_rows(tmp_path: Path) -> None:
    from scripts.core.sovereign_jsonl import iter_jsonl_dict_rows

    p = tmp_path / "z.jsonl"
    p.write_text(
        json.dumps({"source_track": "B", "lab": True}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    rows = list(iter_jsonl_dict_rows(p, track_context="B"))
    assert len(rows) == 1
    assert rows[0]["lab"] is True
