"""Unit tests for scripts/myeongni_16_state_experiment_ledger.py (stdlib validation only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import myeongni_16_state_experiment_ledger as ledger  # noqa: E402


def _valid_minimal() -> dict:
    return {
        "ts_utc": "2026-03-29T12:00:00+00:00",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub": True,
    }


def test_validate_experiment_record_minimal_ok():
    assert ledger.validate_experiment_record(_valid_minimal()) == []


def test_validate_experiment_record_with_optionals_ok():
    rec = {
        **_valid_minimal(),
        "state_id": 3,
        "mapping_target": "bull",
        "vector_4d": {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        "consistency_rate": 0.9,
        "self_contradiction_rate": 0.1,
    }
    assert ledger.validate_experiment_record(rec) == []


def test_validate_experiment_record_consistency_rate_out_of_range():
    r = {**_valid_minimal(), "consistency_rate": 1.5}
    errs = ledger.validate_experiment_record(r)
    assert any("consistency_rate" in e for e in errs)


def test_validate_experiment_record_stub_wrong_type():
    r = _valid_minimal()
    r["stub"] = 42
    errs = ledger.validate_experiment_record(r)
    assert any("stub" in e for e in errs)


def test_validate_experiment_record_boundary_ack_false():
    r = _valid_minimal()
    r["boundary_ack"] = False
    errs = ledger.validate_experiment_record(r)
    assert any("boundary_ack" in e for e in errs)


def test_validate_experiment_record_hypothesis_tier_not_b():
    r = _valid_minimal()
    r["hypothesis_tier"] = "A"
    errs = ledger.validate_experiment_record(r)
    assert any("hypothesis_tier" in e for e in errs)


def test_validate_experiment_record_state_id_out_of_range():
    r = {**_valid_minimal(), "state_id": 0}
    errs = ledger.validate_experiment_record(r)
    assert any("state_id" in e for e in errs)


def test_validate_experiment_record_mapping_target_invalid():
    r = {**_valid_minimal(), "mapping_target": "flat"}
    errs = ledger.validate_experiment_record(r)
    assert any("mapping_target" in e for e in errs)


def test_validate_experiment_record_vector_4d_non_numeric():
    r = {**_valid_minimal(), "vector_4d": {"S": "bad"}}
    errs = ledger.validate_experiment_record(r)
    assert any("vector_4d" in e for e in errs)


def test_validate_experiment_record_missing_key():
    r = {"ts_utc": "x", "hypothesis_tier": "B", "boundary_ack": True}
    errs = ledger.validate_experiment_record(r)
    assert any("missing" in e.lower() for e in errs)


def test_append_myeongni_16_state_experiment_writes_jsonl(tmp_path: Path):
    root = tmp_path
    rec = _valid_minimal()
    out = ledger.append_myeongni_16_state_experiment(
        root, rec, set_ts_if_missing=False
    )
    assert out.parent == root / ledger.WORKSPACE_DATA_REL
    assert out.suffix == ".jsonl"
    text = out.read_text(encoding="utf-8").strip()
    obj = json.loads(text)
    assert obj["hypothesis_tier"] == "B"
    assert ledger.validate_experiment_record(obj) == []


def test_append_raises_on_invalid_record(tmp_path: Path):
    bad = _valid_minimal()
    bad["boundary_ack"] = False
    with pytest.raises(ValueError):
        ledger.append_myeongni_16_state_experiment(tmp_path, bad)
