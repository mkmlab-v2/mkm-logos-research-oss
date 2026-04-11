# @MKM12-METADATA
# Type: Logic
# Purpose: CI lock for GENERAL_PROPHECY_SCHEMA_V1.json (B / OBSERVATION_ONLY rail).
# Keywords: general_prophecy, jsonschema, constitution

"""Validate general prophecy fixture against docs/final/GENERAL_PROPHECY_SCHEMA_V1.json."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"
_FIXTURE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
_SEED5 = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_seed_5_v1.json"
_BRIER_SMOKE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_brier_smoke_v1.json"
_OFFICIAL_SEED = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_official_seed_v1.json"
_MACRO_H2_PACK = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_macro_h2_2026_pack_v1.json"
_PERSONALIZATION_SMOKE = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_personalization_smoke_v1.json"


@pytest.fixture(scope="module")
def _validator():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_general_prophecy_schema_file_exists() -> None:
    assert _SCHEMA_PATH.is_file(), f"missing {_SCHEMA_PATH}"


def test_general_prophecy_fixture_validates(_validator) -> None:
    assert _FIXTURE.is_file(), f"missing {_FIXTURE}"
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])


def test_general_prophecy_fixture_semantics() -> None:
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert doc.get("schema") == "general_prophecy_registry_v1"
    assert doc.get("research_rail") == "B"
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 1
    q = qs[0]
    assert q.get("schema") == "general_prophecy_question_v1"
    assert q.get("outcome_spec", {}).get("kind") == "binary"
    assert q.get("forecasts") and q["forecasts"][0].get("source_kind") == "baseline"


def test_general_prophecy_brier_smoke_fixture_validates(_validator) -> None:
    assert _BRIER_SMOKE.is_file(), f"missing {_BRIER_SMOKE}"
    doc = json.loads(_BRIER_SMOKE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 1
    assert qs[0].get("resolution", {}).get("status") == "resolved"


def test_general_prophecy_macro_h2_2026_pack_fixture_validates(_validator) -> None:
    assert _MACRO_H2_PACK.is_file(), f"missing {_MACRO_H2_PACK}"
    doc = json.loads(_MACRO_H2_PACK.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 5
    ids = [q.get("question_id") for q in qs]
    assert len(set(ids)) == 5


def test_general_prophecy_official_seed_fixture_validates(_validator) -> None:
    assert _OFFICIAL_SEED.is_file(), f"missing {_OFFICIAL_SEED}"
    doc = json.loads(_OFFICIAL_SEED.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 1
    assert qs[0].get("question_id") == "gp_2026_q3_bok_rate_cut_05p"
    assert qs[0].get("resolution", {}).get("status") == "pending"


def test_general_prophecy_seed_5_fixture_validates(_validator) -> None:
    assert _SEED5.is_file(), f"missing {_SEED5}"
    doc = json.loads(_SEED5.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    qs = doc.get("questions")
    assert isinstance(qs, list) and len(qs) == 5
    ids = [q.get("question_id") for q in qs]
    assert len(set(ids)) == 5, "question_id values must be unique"
    for q in qs:
        assert q.get("resolution", {}).get("status") == "pending"
        assert q.get("outcome_spec", {}).get("kind") == "binary"


def test_general_prophecy_personalization_scope_fixture_validates(_validator) -> None:
    assert _PERSONALIZATION_SMOKE.is_file(), f"missing {_PERSONALIZATION_SMOKE}"
    doc = json.loads(_PERSONALIZATION_SMOKE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    q = doc["questions"][0]
    assert q.get("prophecy_track") == "personalized"
    assert q.get("personalization_scope_v1", {}).get("mode") == "cohort"
