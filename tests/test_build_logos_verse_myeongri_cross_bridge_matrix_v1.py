# -*- coding: utf-8 -*-
"""Cross-Bridge top-N matrix smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not (ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl").is_file(),
    reason="corpus missing",
)
def test_build_matrix_top3() -> None:
    from scripts.build_logos_verse_myeongri_cross_bridge_matrix_v1 import build_matrix
    from scripts.build_logos_verse_myeongri_cross_bridge_v1 import (
        DEFAULT_MEDOID_MANIFEST,
        DEFAULT_VERSE_JSONL,
        resolve_human_profiles,
    )

    profiles = resolve_human_profiles(["golden_mdl_gs_v1_0001"])
    doc = build_matrix(
        verse_jsonl=DEFAULT_VERSE_JSONL,
        medoid_manifest=DEFAULT_MEDOID_MANIFEST,
        top_n=3,
        human_profiles=profiles,
    )
    medoid_doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json").read_text(encoding="utf-8")
    )
    top_vid = medoid_doc["global_medoids"][0]["verse_id"]
    assert doc["schema"] == "logos_verse_myeongri_cross_bridge_matrix_v1"
    assert len(doc["rows"]) == 3
    assert doc["rows"][0]["verse_id"] == top_vid
    assert "geometry_by_profile" in doc["rows"][0]
    assert "golden_mdl_gs_v1_0001" in doc["rows"][0]["geometry_by_profile"]
