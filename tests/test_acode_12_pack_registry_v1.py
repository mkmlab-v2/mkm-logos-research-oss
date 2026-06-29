"""A-code 12-pack registry v1 — B-track semantic SSOT skeleton."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/acode_12_pack_registry_v1.json"
SCHEMA = ROOT / "docs/final/schemas/acode_12_pack_registry_v1.schema.json"

FOUR_AI = ("taeyang", "soyang", "taeeum", "soeum")
LIFECYCLES = ("initial", "peak", "exhaustion")


def _load() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8-sig"))


def test_registry_schema_and_grid() -> None:
    doc = _load()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)

    assert doc["research_only"] is True
    assert doc["track_wall"]["bench_4x40_forced_pack_alias_forbidden"] is True
    assert doc["track_wall"]["promotion_to_a_track_allowed"] is False

    packs = doc["packs"]
    assert len(packs) == 12
    ids = [p["pack_id"] for p in packs]
    assert ids == list(range(1, 13))

    for axis in FOUR_AI:
        phases = {p["lifecycle_phase"] for p in packs if p["four_ai_axis"] == axis}
        assert phases == set(LIFECYCLES)

    state_ids = [p["acode_state_id"] for p in packs]
    assert len(state_ids) == len(set(state_ids))

    for p in packs:
        assert p["bench_4x40_alias"] is None


def test_training_contract_router_wired() -> None:
    doc = _load()
    tc = doc["training_contract"]
    fls = doc.get("fact_lock_status", {})
    fstp = doc["routing"]["formula_slot_to_pack"]
    overrides = fstp.get("slot_overrides", {})

    assert fls.get("routing_implemented") is True
    assert fls.get("training_shard_implemented") is True
    assert fstp.get("slot_overrides_status") == "populated"
    assert len(overrides) == 75
    assert tc.get("status") == "router_ready_v1"
    assert tc.get("implemented") is True
    assert "hash_sample_id_mod_12" in tc["deprecated_policies"]
    assert tc.get("target_shard_policy") == "acode_state_deterministic_v1"
    assert tc.get("golden_row_router", {}).get("script_status") == "implemented"
