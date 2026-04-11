# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.6, L:0.5, K:0.55, M:0.4}
# Balance: 84
# Purpose: scm_boming_jiju_lexicon_v1 load and hit tests.
# Keywords: lexicon, sasang, test
from __future__ import annotations

from pathlib import Path

from scripts.core.scm_boming_jiju_lexicon_v1 import (
    SCHEMA_ID,
    boming_jiju_hits_for_text,
    entries_by_constitution,
)


def test_default_lexicon_loads() -> None:
    hits, meta = boming_jiju_hits_for_text("태음인 환자의 호산지기 보존이 중요하다")
    assert meta.get("status") == "ok"
    assert "호산지기" in hits


def test_no_hit() -> None:
    hits, meta = boming_jiju_hits_for_text("일반적인 두통 증상만 기록됨")
    assert meta.get("status") == "ok"
    assert hits == set()


def test_entries_by_constitution() -> None:
    m = entries_by_constitution()
    assert "taeeum_in" in m
    assert len(m["soeum_in"]) >= 1


def test_schema_constant() -> None:
    assert SCHEMA_ID == "scm_boming_jiju_lexicon_v1"


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    hits, meta = boming_jiju_hits_for_text("x", path=tmp_path / "nope.json")
    assert hits == set()
    assert meta.get("status") == "missing"
