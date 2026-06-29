from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_theme_presets_count() -> None:
    presets = json.loads(
        (_ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json").read_text(encoding="utf-8-sig")
    )
    themes = presets.get("themes") or {}
    assert len(themes) >= 12


def test_book_heatmap_schema() -> None:
    path = _ROOT / "reports/logos_canon_book_coverage_heatmap_v1_latest.json"
    if not path.is_file():
        pytest.skip("heatmap not built yet")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_canon_book_coverage_heatmap_v1"
    assert int((doc.get("summary") or {}).get("book_count") or 0) >= 1


def test_commercial_depth_closure_gate_schema() -> None:
    path = _ROOT / "docs/final/artifacts/logos_commercial_depth_closure_v1_latest.json"
    if not path.is_file():
        pytest.skip("closure gate not built yet")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "logos_commercial_depth_closure_v1"
    assert "checks" in doc
