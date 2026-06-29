from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_gpu_hybrid_transition_spec_v1.schema.json"
SPEC_PATH = ROOT / "reports/mkm_gpu_hybrid_transition_spec_v1_latest.json"


@pytest.fixture(scope="module")
def schema_doc() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file()


def test_build_script_materializes_spec() -> None:
    import scripts.build_mkm_gpu_hybrid_transition_spec_v1 as mod

    assert mod.main() == 0
    assert SPEC_PATH.is_file()


def test_spec_required_fields_and_dual_rails() -> None:
    doc = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_gpu_hybrid_transition_spec_v1"
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    assert doc["hypo_label"] == "[HYPO]"
    rail_ids = {r["rail_id"] for r in doc["rails_comparison"]}
    assert rail_ids == {"compression_41k", "prophecy_shadow_31k"}
    for row in doc["rails_comparison"]:
        assert row["single_loop_merge_forbidden"] is True
    assert doc["rail_compression_41k"]["retire_gate"]["41k_disconnect_allowed"] is False
    assert doc["rail_prophecy_shadow_31k"]["vector_layer_additive"]["corpus_retire_forbidden"] is True


def test_spec_validates_against_json_schema(schema_doc: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    doc = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema_doc)
