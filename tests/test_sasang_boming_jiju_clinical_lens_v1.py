# -*- coding: utf-8 -*-
"""B-track: sasang boming-jiju clinical lens pack v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD_PACK = ROOT / "scripts" / "build_sasang_boming_jiju_clinical_lens_pack_v1.py"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "sasang_boming_jiju_clinical_lens_pack_v1.schema.json"


def test_resolve_soeum_label():
    from scripts.core.sasang_boming_jiju_clinical_lens_v1 import (
        build_constitution_slice,
        render_markdown_section,
        resolve_constitution_id,
    )

    assert resolve_constitution_id("소음인") == "soeum_in"
    assert resolve_constitution_id("소음인 (腎大脾小)") == "soeum_in"
    sl = build_constitution_slice("soeum_in")
    assert sl["label_ko"] == "소음인"
    assert any(t.get("term") == "흡취지기" for t in sl["boming_jiju_terms"])
    assert any(t.get("term") == "양난지기" for t in sl["boming_jiju_terms"])
    assert sl.get("cross_ref_deep_links")
    assert sl["cross_ref_deep_links"][0]["deep_link_uri"].startswith("sasang_cross_ref://")
    md = render_markdown_section(
        "소음인",
        ["만성 소화불량", "수족 냉증"],
        "",
    )
    assert "보명지주" in md
    assert "소화·한열" in md
    assert "deep link" in md.lower() or "SASANG_CROSS_REF" in md
    assert "자동 처방" in md or "처방" in md


def test_build_pack_script_writes_latest(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    out = ROOT / "docs" / "final" / "artifacts" / "sasang_boming_jiju_clinical_lens_pack_v1_latest.json"
    cp = subprocess.run(
        [sys.executable, str(BUILD_PACK)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["boundary_contract"]["auto_prescription_forbidden"] is True
    assert "soeum_in" in doc["constitutions"]
