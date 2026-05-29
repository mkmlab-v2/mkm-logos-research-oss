"""Field regime observational snapshot builder (offline)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_build_field_regime_observational_snapshot_v1_smoke(tmp_path: Path) -> None:
    from scripts.build_field_regime_observational_snapshot_v1 import build_snapshot

    chrono_out = tmp_path / "chrono.json"
    chrono_out.write_text(
        json.dumps(
            {
                "schema": "chronology_regime_match_v1",
                "primary_regime_map_observational": "imf",
                "top_match": {"match_id": "exile_and_return"},
                "disagreement_index": 0.42,
            }
        ),
        encoding="utf-8",
    )

    # Monkeypatch chronology runner by pre-seeding output; quad missing → fallback.
    from scripts import build_field_regime_observational_snapshot_v1 as mod

    def fake_chrono(out_path: Path):
        out_path.write_text(chrono_out.read_text(encoding="utf-8"), encoding="utf-8")
        return 0, json.loads(chrono_out.read_text(encoding="utf-8"))

    def fake_quad(*_a, **_k):
        return 2, None

    orig_chrono = mod._run_chronology
    orig_quad = mod._run_quad_rank
    mod._run_chronology = fake_chrono  # type: ignore[assignment]
    mod._run_quad_rank = fake_quad  # type: ignore[assignment]
    try:
        doc = build_snapshot(
            year=2026,
            quad_json=tmp_path / "missing_quad.json",
            chrono_out=tmp_path / "chrono_out.json",
            quad_out=tmp_path / "quad_out.json",
        )
    finally:
        mod._run_chronology = orig_chrono  # type: ignore[assignment]
        mod._run_quad_rank = orig_quad  # type: ignore[assignment]

    assert doc["schema"] == "field_regime_observational_snapshot_v1"
    assert doc["field_layer"]["primary_regime_id_observational"] == "imf"
    assert doc["track_wall"]["live_trading_trigger"] is False
    assert doc["research_only"] is True


def test_build_field_regime_observational_snapshot_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.build_field_regime_observational_snapshot_v1 import main

    out = tmp_path / "snap.json"

    def fake_build(**kwargs):
        doc = {
            "schema": "field_regime_observational_snapshot_v1",
            "field_layer": {"primary_regime_id_observational": "covid"},
        }
        out.write_text(json.dumps(doc), encoding="utf-8")
        return doc

    monkeypatch.setattr(
        "scripts.build_field_regime_observational_snapshot_v1.build_snapshot",
        lambda **kw: fake_build(),
    )
    rc = main(["--output-json", str(out)])
    assert rc == 0
    assert out.is_file()
