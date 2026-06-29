"""Smoke: cosmic meta-architecture UI bundle builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_logos_cosmic_meta_architecture_ui_v1 import build_ui_bundle


def test_build_ui_bundle_schema() -> None:
    doc = build_ui_bundle()
    assert doc["schema"] == "logos_cosmic_meta_architecture_ui_v1"
    assert doc["hypothesis_class"] == "HYPO"
    assert len(doc["force_rows"]) == 4
    assert doc["layers"][0]["id"] == "kernel"


def test_ui_bundle_main_writes_mkm_life_public() -> None:
    from scripts.build_logos_cosmic_meta_architecture_ui_v1 import main

    assert main() == 0
    path = Path("projects/mkm/mkm-life/public/data/logos_cosmic_meta_architecture_ui_v1.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["non_gating"] is True
    assert doc["forbidden_synthesis"] is True
