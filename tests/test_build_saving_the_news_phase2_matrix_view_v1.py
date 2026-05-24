from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_saving_the_news_phase2_matrix_view_v1",
        ROOT / "scripts/build_saving_the_news_phase2_matrix_view_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_resolve_conflict_when_macro_bullish_news_neutral() -> None:
    mod = _load()
    rows = [
        {"lens_id": "news", "non_gating": False, "present": True, "direction_label": "neutral"},
        {"lens_id": "macro", "non_gating": False, "present": True, "direction_label": "bullish_lean"},
        {"lens_id": "logos", "non_gating": True, "present": True, "direction_label": "bearish_lean"},
    ]
    cr = mod.resolve_conflict(rows)
    assert cr["conflict"] is False
    assert cr["dominant_direction_label"] == "bullish_lean"


def test_logos_non_gating_excluded_from_conflict() -> None:
    mod = _load()
    rows = [
        {"lens_id": "sasang", "non_gating": False, "present": True, "direction_label": "bullish_lean"},
        {"lens_id": "macro", "non_gating": False, "present": True, "direction_label": "bearish_lean"},
        {"lens_id": "logos", "non_gating": True, "present": True, "direction_label": "bullish_lean"},
    ]
    cr = mod.resolve_conflict(rows)
    assert cr["conflict"] is True


def test_build_matrix_has_final_action() -> None:
    mod = _load()
    doc = mod.build_matrix()
    assert doc["schema"] == "saving_the_news_phase2_matrix_view_v1"
    assert doc["final_action"]["action"] in {"HOLD", "WATCH", "REDUCE"}
    assert len(doc["matrix_rows"]) >= 5
