"""Schema + determinism checks for Pack 0-B myeongri deterministic LoRA golden set v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "docs/final/schemas/myeongri_deterministic_lora_golden_set_v1.schema.json"
_FIXTURE = _ROOT / "tests/fixtures/myeongri_deterministic_lora_golden_sample_v1.jsonl"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(_SCHEMA.read_text(encoding="utf-8"))


def test_schema_file_exists() -> None:
    assert _SCHEMA.is_file()


def test_fixture_lines_validate_against_schema(schema: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    assert _FIXTURE.is_file()
    for ln in _FIXTURE.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        jsonschema.validate(instance=row, schema=schema)
        assert "calculated_at" not in row["expected_result"]["full_saju"]


def test_build_golden_row_matches_fixture_first_row(schema: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    sys.path.insert(0, str(_ROOT))
    from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict  # noqa: E402

    lines = [ln for ln in _FIXTURE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    want = json.loads(lines[0])
    got = build_golden_row_dict(
        want["birth_instant_utc"],
        want["iana_tz"],
        want.get("is_male", False),
        want["sample_id"],
        want["split"],
    )
    jsonschema.validate(instance=got, schema=schema)
    assert got["expected_result"] == want["expected_result"]


def test_forbidden_supervision_keys_absent() -> None:
    """Pack 0-B: M31-style keys must not appear as top-level supervision hooks."""
    blob = _FIXTURE.read_text(encoding="utf-8").lower()
    for bad in ("hormone_like", "rag_metabolism", "m31_audit", "gematria_seed_trace"):
        assert bad not in blob
