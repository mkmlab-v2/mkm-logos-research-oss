# -*- coding: utf-8 -*-
"""Smoke: intake fusion draft script produces valid bundle + rationale paths."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_patient_intake_fusion_draft_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "patient_intake_fusion_draft_v1.example.json"
INTAKE_SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "patient_intake_fusion_draft_input_v1.schema.json"
_SCHEMA = None


def _schema():
    global _SCHEMA
    if _SCHEMA is None:
        import json as js

        p = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.schema.json"
        _SCHEMA = js.loads(p.read_text(encoding="utf-8"))
    return _SCHEMA


def test_intake_fixture_matches_intake_schema():
    jsonschema = pytest.importorskip("jsonschema")
    raw = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    schema = json.loads(INTAKE_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=raw, schema=schema)


def test_build_patient_intake_fusion_draft_smoke(tmp_path):
    """Runs subprocess (needs full workspace + myeongni builder)."""
    bundle_out = tmp_path / "bundle.json"
    mye = tmp_path / "mye.json"
    rat = tmp_path / "rationale.json"
    md_out = tmp_path / "out.md"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--intake-json",
            str(FIXTURE),
            "--bundle-out",
            str(bundle_out),
            "--myeongni-out",
            str(mye),
            "--rationale-out",
            str(rat),
            "--render-md-out",
            str(md_out),
            "--validate-schema",
            "--validate-policy",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(bundle_out.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "patient_care_bundle_v1"
    assert doc.get("boundary_contract", {}).get("physician_final_authority") is True
    assert doc.get("provenance", {}).get("encounter_ref") == "ENC-DEMO-2026-0516-01"
    assert "스태프 입력 초안" in doc["clinical_soap_v1"]["objective"]["text"]
    slots = {s["slot_id"]: s for s in doc["patient_slots"]}
    assert "근거 요약" in slots["core"]["body_markdown"]
    assert "[HYPO]" in slots["myeongni_ref"]["body_markdown"]
    assert "운영·렌즈 포크" in slots["core"]["body_markdown"]
    rj = json.loads(rat.read_text(encoding="utf-8-sig"))
    assert rj.get("schema") == "patient_intake_fusion_rationale_v1"
    assert rj.get("adjudication_model") == "physician_final_authority_non_auto"
    assert isinstance(rj.get("physician_adj_option_fork_catalog_v1"), list)
    assert rj.get("run_option_snapshot_final", {}).get("post_execution_completed")
    assert rj.get("birth_resolution_v1", {}).get("resolution_mode") == "utc_instant_primary"
    assert rj.get("inputs_echo", {}).get("encounter", {}).get("ref_token") == "ENC-DEMO-2026-0516-01"
    md_out.read_text(encoding="utf-8")

    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(instance=doc, schema=_schema())


def test_build_patient_intake_fusion_draft_brief_flag(tmp_path):
    """Dense is default Track B max; `--brief-output` trims rationale.meta + slots."""
    bundle_out = tmp_path / "bundle_brief.json"
    mye = tmp_path / "mye_b.json"
    rat = tmp_path / "rationale_b.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--intake-json",
            str(FIXTURE),
            "--bundle-out",
            str(bundle_out),
            "--myeongni-out",
            str(mye),
            "--rationale-out",
            str(rat),
            "--validate-schema",
            "--validate-policy",
            "--brief-output",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    rj = json.loads(rat.read_text(encoding="utf-8-sig"))
    assert rj.get("rail") == "Track B"
    assert rj.get("output_density") == "brief"
    assert isinstance(rj.get("physician_adj_option_fork_catalog_v1"), list)
    doc = json.loads(bundle_out.read_text(encoding="utf-8-sig"))
    core = next(s["body_markdown"] for s in doc["patient_slots"] if s["slot_id"] == "core")
    assert "운영·렌즈 포크" in core or "요약" in core


def test_build_patient_intake_fusion_birth_instant_utc_path(tmp_path):
    """UTC+IANA primary profile matches expected local wall (Seoul, demo instant)."""
    intake = tmp_path / "in_utc.json"
    intake.write_text(
        json.dumps(
            {
                "schema": "patient_intake_fusion_draft_v1",
                "version": "1.0.0",
                "encounter": {"ref_token": "ENC-UTC-1"},
                "profile": {
                    "birth_instant_utc": "1990-05-15T05:30:00Z",
                    "iana_tz": "Asia/Seoul",
                    "is_male": True,
                },
                "intake": {
                    "symptoms": ["x"],
                    "situation": "y",
                    "sasang_estimate": {"label": "태음인"},
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    bundle_out = tmp_path / "b.json"
    mye = tmp_path / "m.json"
    rat = tmp_path / "r.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--intake-json",
            str(intake),
            "--bundle-out",
            str(bundle_out),
            "--myeongni-out",
            str(mye),
            "--rationale-out",
            str(rat),
            "--validate-schema",
            "--validate-policy",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    rj = json.loads(rat.read_text(encoding="utf-8-sig"))
    assert rj["birth_resolution_v1"]["resolution_mode"] == "utc_instant_primary"
    assert rj["birth_resolution_v1"]["engine_local_wall_ymdhms"] == [1990, 5, 15, 14, 30, 0]
    doc = json.loads(mye.read_text(encoding="utf-8-sig"))
    assert (doc.get("pillars") or {}).get("day")
