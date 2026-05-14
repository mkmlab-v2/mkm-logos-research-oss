# -*- coding: utf-8 -*-
"""Smoke: CDS envelope validation + assemble with provenance CDS fields."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts" / "build_patient_care_bundle_from_km_cds_chain_v1.py"
CDS_FIXTURE = ROOT / "tests" / "fixtures" / "km_physician_cds_assist_envelope_v1.example.json"
SOAP_FIXTURE = ROOT / "tests" / "fixtures" / "patient_care_bundle_soap_stub_v1.example.json"


@pytest.mark.skipif(not CHAIN.is_file(), reason="chain script missing")
def test_chain_produces_bundle_with_cds_provenance(tmp_path: Path) -> None:
    mye = tmp_path / "myeongni.json"
    bundle = tmp_path / "bundle.json"
    cmd = [
        sys.executable,
        str(CHAIN),
        "--cds-envelope-json",
        str(CDS_FIXTURE),
        "--local",
        "1994",
        "4",
        "10",
        "11",
        "2",
        "0",
        "--iana-tz",
        "Asia/Seoul",
        "--soap-json",
        str(SOAP_FIXTURE),
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
        "--validate-bundle",
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(bundle.read_text(encoding="utf-8-sig"))
    prov = doc.get("provenance") or {}
    assert "km_cds_envelope_path" in prov
    assert "km_cds_envelope_sha256" in prov
    assert len(prov["km_cds_envelope_sha256"]) == 64


@pytest.mark.skipif(not CHAIN.is_file(), reason="chain script missing")
def test_chain_forwards_post_step_flags(tmp_path: Path) -> None:
    apply_s = ROOT / "scripts" / "apply_patient_care_bundle_slot_templates_v1.py"
    validate_s = ROOT / "scripts" / "validate_patient_care_bundle_against_policy_v1.py"
    render_s = ROOT / "scripts" / "render_patient_care_bundle_markdown_v1.py"
    if not (apply_s.is_file() and validate_s.is_file() and render_s.is_file()):
        pytest.skip("post-step helper scripts missing")
    mye = tmp_path / "mye3.json"
    bundle = tmp_path / "bundle3.json"
    out_md = tmp_path / "chain3.md"
    cmd = [
        sys.executable,
        str(CHAIN),
        "--cds-envelope-json",
        str(CDS_FIXTURE),
        "--local",
        "1994",
        "4",
        "10",
        "11",
        "2",
        "0",
        "--iana-tz",
        "Asia/Seoul",
        "--soap-json",
        str(SOAP_FIXTURE),
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
        "--validate-bundle",
        "--apply-slot-templates",
        "--validate-policy",
        "--render-md-out",
        str(out_md),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    assert out_md.is_file()
    assert "# 환자 안내 번들" in out_md.read_text(encoding="utf-8")
    doc = json.loads(bundle.read_text(encoding="utf-8-sig"))
    prov = doc.get("provenance") or {}
    assert prov.get("slot_templates_applied_utc")
    assert prov.get("patient_facing_markdown_path")
