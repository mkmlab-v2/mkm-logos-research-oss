# @MKM12-METADATA
# Type: Logic
# Purpose: MKM theology baseline v1 policy regression.
# Keywords: logos, theology, baseline, track_b, governance

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_POLICY = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_MKM_THEOLOGY_BASELINE_V1.json"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_mkm_theology_baseline_v1.schema.json"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_MKM_THEOLOGY_BASELINE_V1_CONTRACT.json"


def test_policy_contract_exist() -> None:
    assert _POLICY.is_file()
    assert _SCHEMA.is_file()
    assert _CONTRACT.is_file()


def test_policy_validates_schema_and_governance_flags() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    doc = json.loads(_POLICY.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("governance_and_reporting", {}).get("not_a_deregulation_claim") is True
    assert doc.get("non_gating_ack") is True
