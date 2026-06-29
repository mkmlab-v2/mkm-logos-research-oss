"""Tests for MKM paper OCR extract and lens coordinate facts (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_extract_coordinate_facts_ijoeoma_sample():
    from scripts.extract_lens_coordinate_facts_v1 import extract_coordinate_facts

    text = (
        "東武公은 四象醫學의 기틀을 확립하였다. 『東醫壽世保元』에서 太陽人과 少陰人을 "
        "구분하고 性命論과 養生에 관하여 文獻考證하였다."
    )
    facts = extract_coordinate_facts(text, lens="ijeoma", title="sample")
    by_id = {f["field_id"]: f for f in facts}
    assert by_id["four_constitution_axis"]["value"] >= 2
    assert by_id["primary_corpus_cited"]["value"] >= 1
    assert by_id["philosophy_axis"]["value"] >= 1


def test_coordinate_facts_to_markdown_nonempty():
    from scripts.extract_lens_coordinate_facts_v1 import (
        coordinate_facts_to_markdown,
        extract_coordinate_facts,
    )

    text = "四象體質과 格致藁 연구"
    facts = extract_coordinate_facts(text, lens="ijeoma")
    md = coordinate_facts_to_markdown(facts)
    assert "coord_four_constitution_axis" in md
    assert "coordinate_hit_count" in md


def test_extract_coordinate_facts_logos_sample():
    from scripts.extract_lens_coordinate_facts_v1 import extract_coordinate_facts

    text = "요한계시록 12장의 교회 박해와 천년왕국, 에스겔서 상호텍스트, 666 게마트리아"
    facts = extract_coordinate_facts(text, lens="logos", title="sample")
    by_id = {f["field_id"]: f for f in facts}
    assert by_id["revelation_corpus"]["value"] >= 1
    assert by_id["eschatology_axis"]["value"] >= 1


def test_extract_coordinate_facts_myeongri_sample():
    from scripts.extract_lens_coordinate_facts_v1 import extract_coordinate_facts

    text = "연해자평과 적천수의 육친론, 십신과 오행, 사주팔자 대운 비교연구"
    facts = extract_coordinate_facts(text, lens="myeongri", title="sample")
    by_id = {f["field_id"]: f for f in facts}
    assert by_id["classical_corpus"]["value"] >= 2
    assert by_id["yukchin_axis"]["value"] >= 1


def test_mkm_paper_ocr_extract_pdfminer_on_text_pdf():
    from scripts.mkm_paper_ocr_extract_v1 import extract_pdf_text

    sample = ROOT / "data/corpus/ijeoma/secondary/library_capture/2026-06-28/동무_이제마_사상의학과_철학에_대한_고찰.pdf"
    if not sample.is_file():
        pytest.skip("HAAN sample PDF missing")
    text, backend = extract_pdf_text(sample, backend="auto", min_chars=80)
    assert len(text) >= 80
    assert backend in {"pdfminer.six", "pymupdf", "rapidocr-onnxruntime"}
