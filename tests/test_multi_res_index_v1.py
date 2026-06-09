"""Schema and contract smoke for multi_res_index_v1 ([HYPO])."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from multi_res_fills_join_v1 import build_multi_res_index  # noqa: E402

SCHEMA = ROOT / "docs/final/schemas/multi_res_index_v1.schema.json"
CONTRACT = ROOT / "docs/final/artifacts/multi_res_trades_treatment_contract_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/multi_res_trades_smoke_v1.json"


def test_schema_and_contract_exist() -> None:
    assert SCHEMA.is_file()
    assert CONTRACT.is_file()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["research_only"] is True
    assert contract["would_change_active"] is False


def test_build_index_from_fixture_matches_schema_shape() -> None:
    doc = build_multi_res_index(trades_path=FIXTURE, generated_at_utc="2026-06-09T00:00:00Z")
    assert doc["schema"] == "multi_res_index_v1"
    assert doc["meta"]["n_fill_rows"] == 3
    assert doc["meta"]["n_daily_buckets"] == 2
    assert len(doc["coordinate_map"]) == 2
    assert doc["high_res"]["row_summaries"][0]["json_pointer"] == "/0"


def test_schema_validates_example(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = build_multi_res_index(trades_path=FIXTURE, generated_at_utc="2026-06-09T00:00:00Z")
    jsonschema.validate(doc, schema)
