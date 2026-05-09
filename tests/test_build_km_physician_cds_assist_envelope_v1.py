# -*- coding: utf-8 -*-
# Purpose: CDS envelope builder merges constants + payload and passes JSON Schema.
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCR = _ROOT / "scripts" / "build_km_physician_cds_assist_envelope_v1.py"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "km_physician_cds_assist_envelope_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


def _load_mod():
    spec = importlib.util.spec_from_file_location("build_km_physician_cds_assist_envelope_v1", _SCR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_km_physician_cds_assist_envelope_v1"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_minimal_sufficient_envelope_validates() -> None:
    mod = _load_mod()
    doc = mod.build_envelope_from_payload(
        {
            "clinical_question": "What considerations apply before modifying therapy?",
            "evidence_assessment": "sufficient",
        }
    )
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["schema"] == "km_physician_cds_assist_envelope_v1"
    assert doc["evidence_items"] == []


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_partial_requires_gap_notes() -> None:
    mod = _load_mod()
    with pytest.raises(ValueError, match="evidence_gap_notes"):
        mod.build_envelope_from_payload(
            {
                "clinical_question": "Question?",
                "evidence_assessment": "partial",
            }
        )


def test_unknown_payload_key_errors() -> None:
    mod = _load_mod()
    with pytest.raises(ValueError, match="Unknown payload keys"):
        mod.build_envelope_from_payload(
            {
                "clinical_question": "Valid length question here?",
                "evidence_assessment": "sufficient",
                "extra_field": 1,
            }
        )


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_cli_writes_valid_json(tmp_path) -> None:
    inp = tmp_path / "in.json"
    inp.write_text(
        json.dumps(
            {
                "clinical_question": "CLI smoke question?",
                "evidence_assessment": "insufficient",
                "evidence_gap_notes": "No indexed corpus for this edge case in demo snapshot.",
                "evidence_items": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    r = subprocess.run(
        [sys.executable, str(_SCR), "--input-json", str(inp), "-o", str(out), "--pretty"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
