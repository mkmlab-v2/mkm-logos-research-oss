# -*- coding: utf-8 -*-
"""Smoke: assemble_patient_care_bundle_with_myeongni_v1 produces valid patient_care_bundle_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSEMBLE = ROOT / "scripts" / "assemble_patient_care_bundle_with_myeongni_v1.py"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.schema.json"


@pytest.mark.skipif(not ASSEMBLE.is_file(), reason="assemble script missing")
def test_assemble_bundle_validates(tmp_path: Path) -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    mye = tmp_path / "myeongni.json"
    bundle = tmp_path / "bundle.json"
    cmd = [
        sys.executable,
        str(ASSEMBLE),
        "--local",
        "1994",
        "4",
        "10",
        "11",
        "2",
        "0",
        "--iana-tz",
        "Asia/Seoul",
        "--myeongni-out",
        str(mye),
        "--bundle-out",
        str(bundle),
        "--annual-start-year",
        "2026",
        "--annual-years",
        "1",
        "--monthly-months-per-year",
        "3",
        "--validate",
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(bundle.read_text(encoding="utf-8-sig"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["provenance"]["myeongni_report_path"]
    assert doc["patient_slots"][2]["slot_id"] == "myeongni_ref"


@pytest.mark.skipif(not ASSEMBLE.is_file(), reason="assemble script missing")
def test_assemble_post_steps_policy_and_markdown(tmp_path: Path) -> None:
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    apply_s = ROOT / "scripts" / "apply_patient_care_bundle_slot_templates_v1.py"
    validate_s = ROOT / "scripts" / "validate_patient_care_bundle_against_policy_v1.py"
    render_s = ROOT / "scripts" / "render_patient_care_bundle_markdown_v1.py"
    if not (apply_s.is_file() and validate_s.is_file() and render_s.is_file()):
        pytest.skip("post-step helper scripts missing")
    mye = tmp_path / "mye2.json"
    bundle = tmp_path / "bundle2.json"
    out_md = tmp_path / "bundle2.md"
    cmd = [
        sys.executable,
        str(ASSEMBLE),
        "--local",
        "1994",
        "4",
        "10",
        "11",
        "2",
        "0",
        "--iana-tz",
        "Asia/Seoul",
        "--myeongni-out",
        str(mye),
        "--bundle-out",
        str(bundle),
        "--annual-start-year",
        "2026",
        "--annual-years",
        "1",
        "--monthly-months-per-year",
        "3",
        "--validate",
        "--apply-slot-templates",
        "--validate-policy",
        "--render-md-out",
        str(out_md),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out_md.is_file()
    md = out_md.read_text(encoding="utf-8")
    assert "# 환자 안내 번들" in md
    doc = json.loads(bundle.read_text(encoding="utf-8-sig"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    prov = doc["provenance"]
    assert prov.get("slot_templates_applied_utc")
    assert prov.get("slot_templates_json_path")
    assert prov.get("generation_policy_validated_utc")
    assert prov.get("generation_policy_json_path")
    assert prov.get("patient_facing_markdown_written_utc")
    assert prov.get("patient_facing_markdown_path")
