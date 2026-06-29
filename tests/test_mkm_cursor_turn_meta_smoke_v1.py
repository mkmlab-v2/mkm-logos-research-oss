# Keywords: cursor_turn_meta, ltm_graph, shallow_deep, jsonschema

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/mkm_cursor_turn_meta_v1.schema.json"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/mkm_cursor_turn_meta_v1.example.json"
BUILDER = ROOT / "scripts/build_mkm_cursor_turn_meta_stub_v1.py"


def test_schema_file_exists_and_valid():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    assert SCHEMA.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_example_fixture_validates():
    from scripts.build_mkm_cursor_turn_meta_stub_v1 import validate_turn_meta

    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert doc["graph_axis"] == "A_ltm"
    assert validate_turn_meta(doc) == []


def test_build_stub_exit0_and_graph_axis():
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--lane",
            "infra",
            "--continuity-id",
            "test-p1-smoke",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "reports/mkm_cursor_turn_meta_stub_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_cursor_turn_meta_v1"
    assert doc["graph_axis"] == "A_ltm"
    assert doc["lane"] == "infra"
    assert doc["send_gate"] == "HOLD"
    assert len(doc["deep_reads"]) <= 3


def test_infra_lane_rejects_logos_graph_axis_coherence():
    from scripts.build_mkm_cursor_turn_meta_stub_v1 import build_stub, validate_turn_meta

    doc = build_stub(lane="infra", continuity_id="coherence-test", graph_axis="B_logos_bible")
    errs = validate_turn_meta(doc)
    assert any("graph_axis=A_ltm" in e for e in errs)


def test_deep_fetch_next_rejects_graph_slice():
    from scripts.build_mkm_cursor_turn_meta_stub_v1 import build_stub, validate_turn_meta

    doc = build_stub(
        lane="infra",
        continuity_id="slice-deny",
        deep_fetch_next=["data/logos_studio/graph_slice_v1.json"],
    )
    errs = validate_turn_meta(doc)
    assert any("graph_slice" in e for e in errs)
