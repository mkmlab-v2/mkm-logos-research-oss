# -*- coding: utf-8 -*-
"""IJEOMA chunk table harvest for scm_boming_jiju lexicon."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARVEST_SCRIPT = ROOT / "scripts" / "harvest_scm_boming_jiju_from_ijeoma_chunk_table_v1.py"
CHUNK_TABLE = ROOT / "data" / "corpus" / "ijeoma" / "_inventory" / "IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"


@pytest.mark.skipif(not CHUNK_TABLE.is_file(), reason="IJEOMA chunk table missing")
def test_harvest_rejects_section_title_noise():
    from scripts.core.harvest_scm_boming_jiju_from_ijeoma_v1 import (
        _is_rejected_phrase,
        harvest_from_chunk_table,
    )

    assert _is_rejected_phrase("少陰人諸論") is True
    assert _is_rejected_phrase("胃受寒表") is False
    if not CHUNK_TABLE.is_file():
        return
    doc = harvest_from_chunk_table(CHUNK_TABLE, min_freq=2, min_score=50, max_per_constitution=30)
    proposed = doc.get("proposed_lexicon_entries") or []
    terms = {p.get("term") for p in proposed}
    assert "少陰人諸論" not in terms


def test_harvest_produces_soeum_candidates():
    from scripts.core.harvest_scm_boming_jiju_from_ijeoma_v1 import harvest_from_chunk_table

    doc = harvest_from_chunk_table(CHUNK_TABLE, min_freq=2, min_score=50, max_per_constitution=20)
    assert doc["schema"] == "scm_boming_jiju_ijeoma_harvest_v1"
    soeum = doc["candidates_by_constitution"].get("soeum_in") or []
    assert isinstance(soeum, list)
    if soeum:
        assert soeum[0].get("term")


def test_harvest_cli_writes_latest(tmp_path):
    pytest.importorskip("jsonschema")
    if not CHUNK_TABLE.is_file():
        pytest.skip("chunk table missing")
    out = tmp_path / "harvest.json"
    cp = subprocess.run(
        [sys.executable, str(HARVEST_SCRIPT), "--out-json", str(out), "--min-freq", "3"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("proposed_lexicon_entries") is not None
