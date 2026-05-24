"""Public copy facade + gate for Saving the News showroom."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_facade():
    spec = importlib.util.spec_from_file_location(
        "facade", ROOT / "scripts/saving_the_news_public_copy_facade_v1.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_public_facade_strips_theology() -> None:
    mod = _load_facade()
    panel = {
        "headline_anchor": {"headline": "Test"},
        "matrix_rows": [
            {
                "lens_id": "logos",
                "label_ko": "성경(Logos)",
                "non_gating": True,
                "tags": ["[NON_GATING]"],
                "digest": "신실·언약 → 시편 89",
                "direction_label": "neutral",
                "confidence": 0.2,
            }
        ],
        "layer_b": {
            "perspective_slots": [
                {
                    "lens_id": "logos",
                    "non_gating": True,
                    "tags": ["[NON_GATING]", "[HYPO]"],
                    "flavor_ko": "Logos GraphRAG: bridges=2 paths=6 verses=9. 신실·언약 → 시편 89",
                }
            ],
            "coordinator_brief_ko": "명리 관측",
        },
        "flywheel_as_axes": [],
    }
    pub = mod.apply_public_facade_to_panel(panel)
    assert pub["display_mode"] == mod.DISPLAY_PUBLIC
    assert "성경" not in pub["matrix_rows"][0]["label_ko"]
    assert "시편" not in pub["matrix_rows"][0]["digest"]
    assert mod.scan_public_violations(pub) == []


def test_public_copy_gate_on_disk() -> None:
    panel_path = ROOT / "docs/final/artifacts/saving_the_news_matrix_panel_slice_v1_latest.json"
    if not panel_path.is_file():
        pytest.skip("panel slice not generated")
    r = subprocess.run(
        [sys.executable, "scripts/check_saving_the_news_public_copy_gate_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
