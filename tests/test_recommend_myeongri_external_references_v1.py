# -*- coding: utf-8 -*-
from __future__ import annotations

from scripts.recommend_myeongri_external_references_v1 import recommend_entries


def _catalog_sample():
    return {
        "entries": [
            {
                "id": "a",
                "title": "Daewoon calc paper",
                "verification_level": "A_verified_primary",
                "normalization_tags": ["daewoon", "calculation-method"],
                "source_locator": "https://example.com/a",
            },
            {
                "id": "b",
                "title": "General landscape",
                "verification_level": "B_verified_metadata",
                "normalization_tags": ["landscape", "rag-pattern"],
                "source_locator": "https://example.com/b",
            },
            {
                "id": "c",
                "title": "Ten gods quantification",
                "verification_level": "A_verified_primary",
                "normalization_tags": ["ten-gods", "quantification"],
                "source_locator": "https://example.com/c",
            },
        ]
    }


def test_profile_filters_and_ranking():
    recs = recommend_entries(catalog=_catalog_sample(), profile="daewoon", top_n=3)
    ids = [r["id"] for r in recs]
    assert ids[0] == "a"
    assert "c" not in ids


def test_query_boost_keeps_relevant_entry():
    recs = recommend_entries(
        catalog=_catalog_sample(),
        profile="general",
        query="ten gods",
        top_n=2,
    )
    ids = [r["id"] for r in recs]
    assert "c" in ids
