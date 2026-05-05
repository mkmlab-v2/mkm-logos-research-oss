# @MKM12-METADATA
# Type: Logic
# Purpose: Vector index policy stub v1 (slice 3) regression.
# Keywords: logos, vector, policy, track_b

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "run_logos_vector_index_stub_v1.py"
_POLICY = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_VECTOR_INDEX_POLICY_V1.json"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_vector_index_policy_v1.schema.json"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_VECTOR_INDEX_POLICY_V1_CONTRACT.json"
_BUNDLE = _ROOT / "tests" / "fixtures" / "logos_corpus_graph_bundle_minimal_distill_v1.json"


def test_policy_contract_schema_exist() -> None:
    assert _POLICY.is_file()
    assert _SCHEMA.is_file()
    assert _CONTRACT.is_file()


def test_policy_schema_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    doc = json.loads(_POLICY.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_stub_dry_run_with_bundle() -> None:
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--policy",
            str(_POLICY),
            "--bundle-json",
            str(_BUNDLE),
            "--dry-run",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    assert "OK policy=" in cp.stdout
