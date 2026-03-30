"""Smoke tests for Strong mapping (tiny synthetic XML)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.map_master_atoms_lexicon_seed import load_strongs_greek, load_strongs_hebrew


def test_load_strongs_greek(tmp_path: Path):
    xml = tmp_path / "g.xml"
    xml.write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        "<Lexicon><entries>"
        '<entry strongs="00005">'
        ' <greek unicode="Ἀββᾶ" translit="Abbâ"/>'
        "</entry>"
        "</entries></Lexicon>",
        encoding="utf-8",
    )
    m = load_strongs_greek(xml)
    assert m.get("αββα") == ["G5"]


def test_load_strongs_hebrew(tmp_path: Path):
    xml = tmp_path / "h.xml"
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">'
        "<osisText><div>"
        '<w lemma="אָב" ID="H1" xml:lang="heb">אב</w>'
        "</div></osisText></osis>"
    )
    xml.write_text(body, encoding="utf-8")
    m = load_strongs_hebrew(xml)
    assert m.get("אב") == ["H1"]


@pytest.mark.skipif(
    not Path("vault/external_lexicon/sources/openscriptures-strongs/greek").exists(),
    reason="external lexicon not present",
)
def test_real_greek_index_non_empty():
    from scripts.map_master_atoms_lexicon_seed import DEFAULT_LEX_ROOT, _default_paths

    g, _ = _default_paths(DEFAULT_LEX_ROOT)
    m = load_strongs_greek(g)
    assert len(m) > 5000
    assert any(v == ["G5"] for v in m.values())


@pytest.mark.skipif(
    not Path("vault/external_lexicon/sources/openscriptures-strongs/hebrew").exists(),
    reason="external lexicon not present",
)
def test_real_hebrew_index_non_empty():
    from scripts.map_master_atoms_lexicon_seed import DEFAULT_LEX_ROOT, _default_paths

    _, h = _default_paths(DEFAULT_LEX_ROOT)
    m = load_strongs_hebrew(h)
    assert len(m) > 5000
