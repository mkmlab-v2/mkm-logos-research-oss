"""Smoke tests for clinic lifestyle management print renderer v2."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / "scripts" / "render_clinic_lifestyle_management_print_v1.py"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/clinic_lifestyle_management_post_miscarriage_soeum_v2.example.json"
SPEC = ROOT / "docs/final/artifacts/clinic_lifestyle_management_format_spec_v2.json"


def _load_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_lifestyle", RENDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_fixture_renders_without_myeongni_patient_terms(tmp_path: Path) -> None:
    mod = _load_module()
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    html = mod.render_html(data, spec)

    forbidden = spec["language_policy"]["patient_print_forbidden_terms_ko"]
    for term in forbidden:
        assert term not in html, f"forbidden patient term in print: {term!r}"

    assert "회복·생활관리" in html
    assert "영양 · 식사 패턴" in html
    assert "子女星" not in html
    assert "internal_reference" not in html

    out = tmp_path / "out.html"
    out.write_text(html, encoding="utf-8")
    assert out.stat().st_size > 500
