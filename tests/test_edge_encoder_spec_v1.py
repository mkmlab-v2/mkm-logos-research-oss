# Edge Encoder spec v1 — schema + determinism smoke

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC_SCHEMA = ROOT / "docs/final/schemas/edge_encoder_spec_v1.schema.json"
COORD_SCHEMA = ROOT / "docs/final/schemas/edge_encoder_coord_wire_v1.schema.json"
BUILD_SCRIPT = ROOT / "scripts/build_edge_encoder_spec_v1.py"
DETERMINISM_SCRIPT = ROOT / "scripts/check_edge_encoder_coord_wire_determinism_v1.py"
SPEC_OUT = ROOT / "docs/final/artifacts/edge_encoder_spec_v1_latest.json"
COORD_EXAMPLE = ROOT / "docs/final/artifacts/coord_wire_packet_example_v1_latest.json"


def test_build_edge_encoder_spec_exit_0():
    r = subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(SPEC_OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "edge_encoder_spec_v1"
    assert doc["maturity"] == "sdk_alpha"
    assert doc["send_gate"] == "HOLD"
    assert doc["client_obligations"]["emit_coord_wire_only"] is True
    assert doc["mask_hybrid_determinism"]["backend"] == "mkm_candidate_pool"


def test_edge_encoder_spec_jsonschema():
    jsonschema = pytest.importorskip("jsonschema")
    doc = json.loads(SPEC_OUT.read_text(encoding="utf-8"))
    schema = json.loads(SPEC_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(doc)


def test_coord_wire_example_matches_coord_schema():
    jsonschema = pytest.importorskip("jsonschema")
    example = json.loads(COORD_EXAMPLE.read_text(encoding="utf-8"))
    wire = example["coord_wire_minimal"]
    schema = json.loads(COORD_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(wire)


def test_coord_wire_determinism_gate_exit_0():
    r = subprocess.run([sys.executable, str(DETERMINISM_SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_mask_hybrid_determinism_gate_exit_0():
    from scripts.edge_encoder_spec_v1_lib import check_mask_hybrid_determinism, expected_mask_backend

    errors, summary = check_mask_hybrid_determinism(workspace_root=ROOT, max_cases=3)
    assert errors == [], errors
    assert summary.get("case_count", 0) >= 1
    assert summary.get("backend_expected") == expected_mask_backend(workspace_root=ROOT)


def test_mask_hybrid_determinism_script_exit_0():
    script = ROOT / "scripts/check_edge_encoder_mask_hybrid_determinism_v1.py"
    r = subprocess.run([sys.executable, str(script), "--max-cases", "3"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_lib_validate_coord_wire_no_errors():
    from scripts.edge_encoder_spec_v1_lib import (
        check_coord_wire_determinism,
        load_coord_wire_from_example,
        validate_coord_wire_minimal,
    )

    wire = load_coord_wire_from_example()
    assert validate_coord_wire_minimal(wire) == []
    assert check_coord_wire_determinism(wire, workspace_root=ROOT) == []
