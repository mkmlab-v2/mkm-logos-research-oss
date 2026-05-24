"""B-track chronology regime match v1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def mod():
    import scripts.build_chronology_regime_match_v1 as m

    return m


def test_chronology_match_produces_ranked_hypo(tmp_path: Path, mod) -> None:
    chrono = tmp_path / "chrono.json"
    chrono.write_text(
        json.dumps(
            {
                "schema": "logos_chronology_v1",
                "eras": [
                    {
                        "era_id": "exile_and_return",
                        "label_ko": "포로·귀환",
                        "theme_tags": ["rebuild", "return", "restoration"],
                    },
                    {
                        "era_id": "patriarch_covenant_arc",
                        "label_ko": "족장",
                        "theme_tags": ["covenant", "promise"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    packet = tmp_path / "packet.json"
    packet.write_text(
        json.dumps(
            {
                "summary_ko": "infrastructure rebuild wall regulation reshoring supply chain restoration",
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "match.json"
    rc = mod.main(
        [
            "--chronology-json",
            str(chrono),
            "--macro-packet-json",
            str(packet),
            "--macro-json",
            str(tmp_path / "missing_macro.json"),
            "--news-json",
            str(tmp_path / "missing_news.json"),
            "--regime-map-json",
            str(tmp_path / "missing_regime.json"),
            "--output-json",
            str(out),
        ]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "chronology_regime_match_v1"
    assert doc["research_only"] is True
    assert doc["top_match"]["match_id"] in {"nehemiah_rebuild_hypo", "exile_and_return"}
    assert 0.0 <= doc["disagreement_index"] <= 1.0
