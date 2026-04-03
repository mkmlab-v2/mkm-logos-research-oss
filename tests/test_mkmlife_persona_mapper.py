"""Smoke tests for mkmlife A-Code Persona 12 UX layer."""

from tools.mkmlife.persona_mapper import (
    PersonaMapper,
    resolve_persona_by_branch_index,
    resolve_persona_by_constitution_pathology,
    ui_primary_label,
)


def test_constitution_pathology_maps_to_12_personas():
    assert resolve_persona_by_constitution_pathology("태양인", "SL")["persona_id"] == "P01"
    assert resolve_persona_by_constitution_pathology("소음인", "DL")["persona_id"] == "P12"


def test_branch_index_round_trip():
    p0 = resolve_persona_by_branch_index(0)
    assert p0["earthly_branch"] == "zi"
    assert p0["persona_id"] == "P01"
    p11 = resolve_persona_by_branch_index(11)
    assert p11["persona_id"] == "P12"


def test_ui_primary_label_modern():
    p = resolve_persona_by_constitution_pathology("태음인", "IL")
    assert "안정" in ui_primary_label(p) or "우선" in ui_primary_label(p)


def test_persona_mapper_class():
    m = PersonaMapper()
    x = m.by_constitution_pathology("소양인", "DL")
    assert x["persona_id"] == "P09"
