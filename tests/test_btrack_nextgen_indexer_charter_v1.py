from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/btrack_nextgen_indexer_charter_v1.schema.json"
CHARTER_PATH = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"
BENCH_PATH = ROOT / "reports/btrack_nextgen_indexer_parallel_bench_v1_latest.json"


@pytest.fixture(scope="module")
def schema_doc() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.is_file()


def test_build_charter_materializes() -> None:
    import scripts.build_btrack_nextgen_indexer_charter_v1 as mod

    assert mod.main() == 0
    assert CHARTER_PATH.is_file()


def test_charter_three_arms_and_gates() -> None:
    doc = json.loads(CHARTER_PATH.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_nextgen_indexer_charter_v1"
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    arm_ids = {a["arm_id"] for a in doc["parallel_bench_arms"]}
    assert arm_ids == {
        "legacy_discrete_41k",
        "gpu_semantic_poc",
        "nextgen_latent_indexer",
    }
    assert doc["retire_gates"]["legacy_41k_disconnect_allowed"] is False
    snap = doc["frozen_baseline"]["metrics_snapshot"]
    assert snap["global_token_saving_rate"] is not None
    assert snap["avg_reconstruction_fidelity_jaccard"] is not None


def test_charter_validates_against_json_schema(schema_doc: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    doc = json.loads(CHARTER_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema_doc)


def test_parallel_bench_chain_dry_run() -> None:
    import sys

    import scripts.run_btrack_nextgen_indexer_parallel_bench_chain_v1 as mod

    plan = mod.build_plan(execute=False)
    assert plan["research_only"] is True
    assert plan["arms"]["nextgen_latent_indexer"]["status"] == "charter_only"

    old = sys.argv
    try:
        sys.argv = ["run_btrack_nextgen_indexer_parallel_bench_chain_v1.py", "--dry-run"]
        assert mod.main() == 0
    finally:
        sys.argv = old
    assert BENCH_PATH.is_file()
