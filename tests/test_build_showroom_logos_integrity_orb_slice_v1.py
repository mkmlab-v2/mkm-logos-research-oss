# Keywords: build_showroom_logos_integrity_orb_slice_v1, logos, integrity, NON_GATING

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_showroom_logos_integrity_orb_slice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/showroom_logos_integrity_orb_slice_v1.schema.json"
ENTRY13 = ROOT / "reports/deep_research_entry_13_ps5_8_9_shadow_supplement_v1_latest.json"
ENTRY16 = ROOT / "reports/deep_research_entry_16_ezra_2_54_waiting_queue_plan_v1_latest.json"


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert SCHEMA.is_file()
    assert ENTRY13.is_file()
    assert ENTRY16.is_file()


def test_build_slice_default_out(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out), "--out-artifact", str(tmp_path / "art.json")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_logos_integrity_orb_slice_v1"
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert doc["rail_status"]["verified_anchor_achieved"] is False
    assert doc["rail_status"]["send_gate"] == "HOLD"
    assert doc["stats"]["preset_count"] >= 2
    entry_ids = {p["entry_id"] for p in doc["presets"]}
    assert entry_ids == {"ENTRY_13", "ENTRY_16"}
    gap_nodes = [n for n in doc["nodes"] if n["kind"] == "gap"]
    assert len(gap_nodes) >= 2


def test_build_slice_json_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "slice2.json"
    subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--out-json",
            str(out),
            "--out-artifact",
            str(tmp_path / "art2.json"),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
