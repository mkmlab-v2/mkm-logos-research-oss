"""Charter R5 — B2B han clinic training Google Form schema tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/b2b_han_clinic_training_google_form_v1.schema.json"
SCRIPT = ROOT / "scripts/build_b2b_han_clinic_training_google_form_v1.py"


def test_build_and_validate_passive_corral(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "form.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    corral = doc["passive_corral"]
    assert corral["send_gate"] == "HOLD"
    assert corral["patient_funnel_allowed"] is False
    assert corral["akom_credential_claim_forbidden"] is True
    assert len(doc["sections"]) >= 4
    ack_fields = [
        f["field_id"]
        for s in doc["sections"]
        for f in s["fields"]
        if f.get("forbidden_claim_guard")
    ]
    assert "ack_no_patient_funnel" in ack_fields
    assert "ack_logos_non_gating" in ack_fields


def test_register_script_exists():
    assert (ROOT / "scripts/build_b2b_han_clinic_training_google_form_v1.py").is_file()
