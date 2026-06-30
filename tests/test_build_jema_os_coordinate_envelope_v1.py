"""JEMA OS coordinate envelope v1 builder + schema smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_jema_os_coordinate_envelope_v1.py"
SCHEMA = ROOT / "docs/final/schemas/jema_os_coordinate_envelope_v1.schema.json"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/jema_os_coordinate_envelope_v1.example.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_jema_os_coordinate_envelope_v1 import (  # noqa: E402
    build_envelope,
    map_read_depth,
)


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_map_read_depth_skim_deep_hold():
    skim = map_read_depth("skim")
    assert skim["resolution_tier"] == "low_res"
    assert skim["required_ltm_depth"] == 0.15
    deep = map_read_depth("deep")
    assert deep["resolution_tier"] == "high_res"
    assert deep["required_ltm_depth"] == 0.65
    hold = map_read_depth("hold")
    assert hold["resolution_tier"] == "hold_gate"


def test_example_fixture_validates_against_schema():
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=_schema())


def test_build_envelope_in_memory_schema_and_guard():
    doc = build_envelope(read_depth="skim", lane="oracle")
    jsonschema.validate(instance=doc, schema=_schema())
    assert doc["send_gate"] == "HOLD"
    assert doc["fail_comp_004_guard"]["compression_kpi_weight_in_inference"] == 0
    assert doc["fail_comp_004_guard"]["lens_score_headline_merge"] is False
    assert doc["ltm_pin"]["inject_policy"] == "single_node_only"
    assert doc["a2a_peer"]["optional"] is True


def test_build_envelope_a2a_bounded_lane_cross_ref():
    doc = build_envelope(read_depth="skim", lane="oracle")
    a2a = doc["a2a_peer"]
    assert a2a.get("bounded_lane_loop_ref")
    if (ROOT / "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_oracle_v1_latest.md").is_file():
        assert a2a.get("peer_handoff_pointer")


def test_builder_mirror_no1kmedi_exit_zero():
    skim_path = ROOT / "projects/no1kmedi/public/data/jema_os_coordinate_envelope_skim_v1.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--mirror-all-depths",
            "--lane",
            "oracle",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert skim_path.is_file()
    doc = json.loads(skim_path.read_text(encoding="utf-8"))
    assert doc["read_depth"] == "skim"


def test_builder_cli_exit_zero():
    out = ROOT / "reports/_test_jema_os_coordinate_envelope_v1.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--out",
            str(out),
            "--read-depth",
            "deep",
            "--lane",
            "oracle",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=_schema())
    assert doc["read_depth"] == "deep"
    assert doc["umr_binding"]["resolution_tier"] == "high_res"


def test_invalid_read_depth_raises():
    with pytest.raises(ValueError):
        map_read_depth("invalid")
