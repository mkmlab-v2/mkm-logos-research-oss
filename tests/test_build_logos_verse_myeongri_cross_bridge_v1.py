# -*- coding: utf-8 -*-
"""Cross-Bridge v0: verse OS 4D vs golden Myeongri 4D geometry report."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_verse_myeongri_cross_bridge_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_verse_myeongri_cross_bridge_v1.schema.json"
FIXTURE = ROOT / "tests" / "data" / "logos_verse_myeongri_cross_bridge_fixture_v1.json"


def _validate(doc: dict, schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_fixture_matches_schema() -> None:
    assert FIXTURE.is_file(), f"missing {FIXTURE}"
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _validate(doc, SCHEMA)
    assert doc["hypothesis_tier"] == "B"
    assert doc["track_wall"]["ready_for_external_send"] is False
    assert "l2_os_human" in doc["geometry"]


def test_build_report_pure_geometry() -> None:
    from scripts.build_logos_verse_myeongri_cross_bridge_v1 import build_report

    verse_row = {
        "verse_id": "Lev.23.9",
        "lane": "canon",
        "vector_4d": {"S": 0.4, "L": 0.3, "K": 0.2, "M": 0.1},
        "mapping": {"recipe_id": "verse_decoded_v2_legacy"},
    }
    human = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    doc = build_report(
        verse_row=verse_row,
        human_vec=human,
        blend_weight_myeongri=0.5,
        verse_jsonl=ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl",
        medoid_manifest=ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json",
    )
    _validate(doc, SCHEMA)
    assert doc["verse_os"]["verse_id"] == "Lev.23.9"
    assert doc["geometry"]["cosine_os_human"] <= 1.0
    assert doc["blend_optional"] is not None


@pytest.mark.skipif(
    not (ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl").is_file(),
    reason="corpus jsonl not present",
)
def test_script_integration() -> None:
    out = ROOT / "reports" / "tmp_cross_bridge_integration_v1.json"
    if out.is_file():
        out.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out-json",
            str(out),
            "--validate-schema",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    medoid_doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc["verse_os"]["verse_id"] == medoid_doc["global_medoids"][0]["verse_id"]
    assert doc["human_terminal"]["profile_id"] == "golden_mdl_gs_v1_0001"
