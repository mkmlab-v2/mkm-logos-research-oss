"""HAAN logos gematria lexicon join skeleton tests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_haan_logos_gematria_lexicon_join_v1 import (
    build_join,
    discover_gematria_tier0,
    extract_number_mentions,
)

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"


def test_discover_gematria_tier0_has_two_papers():
    paths = discover_gematria_tier0()
    stems = {p.stem for p in paths}
    assert any("성경에_나타난_숫자" in s for s in stems)
    assert any("성서게마트리아" in s for s in stems)


def test_extract_number_mentions_from_sample():
    text = "요한복음 21장의 153, 요한계시록 13장의 666"
    assert extract_number_mentions(text) == [153, 666]


def test_build_join_beast_666_links_g5516():
    if not LEXICON.is_file():
        return
    tier0 = discover_gematria_tier0()
    numbers_paper = next(p for p in tier0 if "성경에_나타난_숫자" in p.stem)
    doc = build_join(lexicon_path=LEXICON, tier0_paths=[numbers_paper], reverse_cap=3)
    assert doc["schema"] == "haan_logos_gematria_lexicon_join_v1"
    paper = doc["papers"][0]
    beast = next(a for a in paper["number_anchor_joins"] if a["anchor_id"] == "beast_666")
    assert beast["mentioned_in_tier0"] is True
    assert beast["strongs_hits"]
    assert beast["strongs_hits"][0]["strongs"] == "G5516"
    assert beast["strongs_hits"][0]["gematria_traditional"]["isopsephy_standard"] == 666
    assert beast["strongs_hits"][0]["vector_4d"]["S"] > 0


def test_build_join_153_14_optional_reverse():
    if not LEXICON.is_file():
        return
    tier0 = discover_gematria_tier0()
    numbers_paper = next(p for p in tier0 if "성경에_나타난_숫자" in p.stem)
    doc = build_join(lexicon_path=LEXICON, tier0_paths=[numbers_paper], reverse_cap=5)
    paper = doc["papers"][0]
    fish = next(a for a in paper["number_anchor_joins"] if a["anchor_id"] == "fish_153")
    gen14 = next(a for a in paper["number_anchor_joins"] if a["anchor_id"] == "genealogy_14")
    assert fish["mentioned_in_tier0"] is True
    assert gen14["mentioned_in_tier0"] is True
    assert fish["reverse_lexicon_hits"], "expected optional reverse hits for 153"
    assert gen14["reverse_lexicon_hits"], "expected optional reverse hits for 14"


def test_cli_exit_zero(tmp_path):
    if not LEXICON.is_file():
        return
    import subprocess
    import sys

    out = tmp_path / "join.json"
    proc = subprocess.run(
        [sys.executable, "scripts/build_haan_logos_gematria_lexicon_join_v1.py", "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["papers"]
