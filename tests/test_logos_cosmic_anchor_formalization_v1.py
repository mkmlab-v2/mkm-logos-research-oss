"""Logos Cosmic Anchor formalization v1 — Wave 1 pilot schema + builder regression."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/logos_cosmic_anchor_formalization_v1.schema.json"
OUT_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_pilot_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_pilot_v1_manifest_latest.json"
BUILD = ROOT / "scripts/build_logos_cosmic_anchor_pilot_v1.py"
PILOT_STEMS = ("seed", "light", "way")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMA)
    jsonschema.Draft7Validator.check_schema(schema)


@pytest.mark.parametrize("stem", PILOT_STEMS)
def test_pilot_anchor_validates_against_schema(stem: str) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(SCHEMA)
    doc = _load(OUT_DIR / f"{stem}.json")
    jsonschema.Draft7Validator(schema).validate(doc)


def test_fact_lock_and_track_wall() -> None:
    for stem in PILOT_STEMS:
        doc = _load(OUT_DIR / f"{stem}.json")
        fl = doc["fact_lock"]
        assert fl["hypothesis_class"] == "HYPO"
        assert fl["forbidden_synthesis"] is True
        assert fl["non_gating"] is True
        assert fl["ready_for_external_send"] is False
        tw = doc["track_wall"]
        assert tw["a_track_auto_promotion"] is False
        assert tw["live_trading_trigger"] is False


def test_layers_separated_no_synthesis_field() -> None:
    for stem in PILOT_STEMS:
        doc = _load(OUT_DIR / f"{stem}.json")
        assert "logos_layer" in doc["layers"]
        assert "sasang_myeongni_layer" in doc["layers"]
        assert "synthesis" not in doc
        assert len(doc["kernel_alignment"]) <= 3
        for row in doc["kernel_alignment"]:
            assert 0.0 <= row["similarity"] <= 1.0
            assert "[HYPO]" in row["alignment_note_ko"]


def test_vector_4d_simplex_sum_near_one() -> None:
    for stem in PILOT_STEMS:
        v = _load(OUT_DIR / f"{stem}.json")["vector_4d"]
        total = v["S"] + v["L"] + v["K"] + v["M"]
        assert abs(total - 1.0) < 1e-6


def test_manifest_lookup_three_anchors() -> None:
    m = _load(MANIFEST)
    assert m["schema"] == "logos_cosmic_anchor_pilot_v1_manifest"
    assert m["anchor_count"] == 3
    assert m["forbidden_synthesis"] is True
    assert set(m["paths"].keys()) == set(PILOT_STEMS)
    assert m["lookup_by_verse_ref"]["Jhn.12.24"] == "cosmic_anchor_seed_jhn_12_24"
    assert m["lookup_by_verse_ref"]["Jhn.1.5"] == "cosmic_anchor_light_jhn_1_5"
    assert m["lookup_by_verse_ref"]["Jhn.14.6"] == "cosmic_anchor_way_jhn_14_6"


def test_builder_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_mkmlife_public_sync() -> None:
    mkmlife_manifest = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_pilot_v1_manifest_latest.json"
    assert mkmlife_manifest.is_file()
    for stem in PILOT_STEMS:
        assert (ROOT / f"projects/mkm/mkm-life/public/data/logos_cosmic_anchor_pilot_v1/{stem}.json").is_file()


def test_vector_4d_has_spread_on_at_least_one_anchor() -> None:
    spreads = []
    for stem in PILOT_STEMS:
        v = _load(OUT_DIR / f"{stem}.json")["vector_4d"]
        vals = [v["S"], v["L"], v["K"], v["M"]]
        spreads.append(max(vals) - min(vals))
    assert max(spreads) > 0.005, spreads


def test_manifest_preset_lookup() -> None:
    m = _load(MANIFEST)
    assert m.get("lookup_by_preset_id", {}).get("job_suffering_reason") == "cosmic_anchor_seed_jhn_12_24"


def test_normalize_intensity_budget_in_unit_interval() -> None:
    for stem in PILOT_STEMS:
        doc = _load(OUT_DIR / f"{stem}.json")
        for row in doc["kernel_alignment"]:
            if row["param"] == "intensity_budget":
                val = row["draft"]["intensity_budget"]
                assert 0.0 <= val <= 1.0
