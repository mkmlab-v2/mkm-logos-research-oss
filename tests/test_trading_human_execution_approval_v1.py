# @MKM12-METADATA
# Type: Logic
# Purpose: CI lock for trading_human_execution_approval_v1 schema + validator (no live orders).
# Keywords: trading, human-in-the-loop, jsonschema, bulkhead

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "docs" / "final" / "artifacts" / "schemas" / "trading_human_execution_approval_v1.schema.json"
_EX_GO = _ROOT / "docs" / "final" / "artifacts" / "trading_human_execution_approval_v1_example_GO.json"
_EX_NO_GO = _ROOT / "docs" / "final" / "artifacts" / "trading_human_execution_approval_v1_example_NO_GO.json"
_FIXTURE = _ROOT / "tests" / "fixtures" / "trading_execution_proposal_sample_v1.json"
_VALIDATE = _ROOT / "scripts" / "validate_trading_human_execution_approval_v1.py"


@pytest.fixture(scope="module")
def _validator():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_schema_and_example_files_exist() -> None:
    for p in (_SCHEMA, _EX_GO, _EX_NO_GO, _FIXTURE, _VALIDATE):
        assert p.is_file(), f"missing {p}"


def test_example_go_validates_schema(_validator) -> None:
    doc = json.loads(_EX_GO.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])


def test_example_no_go_validates_schema(_validator) -> None:
    doc = json.loads(_EX_NO_GO.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])


def test_validator_cli_example_go_ok() -> None:
    r = subprocess.run(
        [sys.executable, str(_VALIDATE), "--approval", str(_EX_GO)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_validator_cli_go_hash_mismatch(tmp_path) -> None:
    bad = tmp_path / "approval.json"
    doc = json.loads(_EX_GO.read_text(encoding="utf-8"))
    doc["proposal_body_sha256"] = "a" * 64
    bad.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_VALIDATE), "--approval", str(bad)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2, r.stderr + r.stdout


def test_validator_cli_go_expired(tmp_path) -> None:
    exp = tmp_path / "approval.json"
    doc = json.loads(_EX_GO.read_text(encoding="utf-8"))
    doc["valid_until_utc"] = "2020-01-01T00:00:00Z"
    exp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_VALIDATE), "--approval", str(exp)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 3, r.stderr + r.stdout


def test_fixture_sha_matches_example_go() -> None:
    import hashlib

    h = hashlib.sha256(_FIXTURE.read_bytes()).hexdigest()
    doc = json.loads(_EX_GO.read_text(encoding="utf-8"))
    assert doc["proposal_body_sha256"] == h
