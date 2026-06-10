"""Unit tests for personadiary live smoke hub-footer probe."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_smoke_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_personadiary_live_ops_smoke_v1.py"
    spec = importlib.util.spec_from_file_location("personadiary_live_ops_smoke", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_hub_footer_probe_ok_when_markers_present():
    mod = _load_smoke_module()
    html = (
        '<div class="pd-hub-footer">MKM 관련 제품'
        '<a href="https://mkmlife.com">mkmlife</a>'
        'JEMA AI 브랜드'
        'mkmlife.com과 API·데이터를 합치지 않습니다.'
        "</div>"
    )
    ok, detail = mod.hub_footer_probe_ok(html)
    assert ok is True
    assert "markers ok" in detail


def test_hub_footer_probe_fails_when_boundary_missing():
    mod = _load_smoke_module()
    html = (
        "pd-hub-footer MKM 관련 제품 JEMA AI 브랜드 mkmlife.com"
        "without boundary phrase"
    )
    ok, detail = mod.hub_footer_probe_ok(html)
    assert ok is False
    assert "boundary" in detail


def test_phase2_html_markers_constant():
    mod = _load_smoke_module()
    assert "pd-ritual-draw" in mod.PHASE2_HTML_MARKERS
