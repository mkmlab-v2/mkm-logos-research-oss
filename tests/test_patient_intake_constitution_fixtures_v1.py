# -*- coding: utf-8 -*-
"""Regression: four-constitution clinical intake fixtures include boming-jiju lens pack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_patient_intake_fusion_draft_v1.py"
BUILD_LENS_PACK = ROOT / "scripts" / "build_sasang_boming_jiju_clinical_lens_pack_v1.py"

CASES = [
    (
        "tests/fixtures/patient_intake_taeeum_clinical_v1.example.json",
        "taeeum_in",
        "태음인",
        "호산지기",
        "폐·간",
    ),
    (
        "tests/fixtures/patient_intake_soyang_clinical_v1.example.json",
        "soyang_in",
        "소양인",
        "담기",
        "脾大胃小",
    ),
    (
        "tests/fixtures/patient_intake_taeyang_clinical_v1.example.json",
        "taeyang_in",
        "태양인",
        "심기",
        "태양",
    ),
]


@pytest.fixture(scope="module", autouse=True)
def _lens_pack_built():
    subprocess.run(
        [sys.executable, str(BUILD_LENS_PACK)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "fixture_rel,constitution_id,label_ko,anchor_term,axis_snippet",
    CASES,
)
def test_clinical_intake_includes_boming_jiju_lens(
    tmp_path: Path,
    fixture_rel: str,
    constitution_id: str,
    label_ko: str,
    anchor_term: str,
    axis_snippet: str,
) -> None:
    fixture = ROOT / fixture_rel
    assert fixture.is_file()
    bundle_out = tmp_path / "bundle.json"
    rat_out = tmp_path / "rationale.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--intake-json",
            str(fixture),
            "--bundle-out",
            str(bundle_out),
            "--myeongni-out",
            str(tmp_path / "myeongni.json"),
            "--rationale-out",
            str(rat_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(bundle_out.read_text(encoding="utf-8-sig"))
    sasang = next(s for s in doc["patient_slots"] if s["slot_id"] == "sasang")
    body = sasang["body_markdown"]
    assert anchor_term in body
    assert axis_snippet in body
    assert "보명지주" in body
    assert "자동 추천 없음" in body or "처방" in body
    rat = json.loads(rat_out.read_text(encoding="utf-8-sig"))
    cc = rat.get("cross_checks_v1") or {}
    assert cc.get("myeongni_sasang_clinical_v1", {}).get("constitution_id") == constitution_id
    assert cc.get("myeongni_sasang_clinical_v1", {}).get("status") == "match"
    assert cc.get("sasang_boming_jiju_lens_v1", {}).get("deep_link_count", 0) >= 1
    intake = json.loads(fixture.read_text(encoding="utf-8-sig"))
    assert intake["intake"]["sasang_estimate"]["label"] == label_ko
