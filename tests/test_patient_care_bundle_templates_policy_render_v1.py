# -*- coding: utf-8 -*-
"""Smoke: slot templates, generation policy gate, Markdown render for patient_care_bundle_v1."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_patient_care_bundle_slot_templates_v1.py"
VALIDATE = ROOT / "scripts" / "validate_patient_care_bundle_against_policy_v1.py"
RENDER = ROOT / "scripts" / "render_patient_care_bundle_markdown_v1.py"
MINIMAL = ROOT / "docs" / "final" / "schemas" / "patient_care_bundle_v1.minimal.example.json"
POLICY = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_generation_policy_v1.default.json"
TEMPLATES = ROOT / "docs" / "final" / "artifacts" / "patient_care_bundle_slot_templates_ko_v1.json"


@pytest.mark.skipif(
    not (APPLY.is_file() and VALIDATE.is_file() and RENDER.is_file()),
    reason="patient bundle helper scripts missing",
)
def test_apply_templates_subst_json(tmp_path: Path) -> None:
    bundle_in = tmp_path / "in.json"
    bundle_out = tmp_path / "out.json"
    subst = tmp_path / "subst.json"
    src = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    for s in src["patient_slots"]:
        if s["slot_id"] == "myeongni_ref":
            s["body_markdown"] = ""
    bundle_in.write_text(json.dumps(src, ensure_ascii=False, indent=2), encoding="utf-8")
    subst.write_text(
        json.dumps(
            {
                "DAY_MASTER_STEM": "甲",
                "YEAR_PILLAR": "甲子",
                "MONTH_PILLAR": "乙丑",
                "DAY_PILLAR": "丙寅",
                "HOUR_PILLAR": "丁卯",
                "MYEONGNI_REPORT_PATH": "reports/myeongni_stub.json",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        str(APPLY),
        "--bundle-in",
        str(bundle_in),
        "--bundle-out",
        str(bundle_out),
        "--templates-json",
        str(TEMPLATES),
        "--subst-json",
        str(subst),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(bundle_out.read_text(encoding="utf-8"))
    mye = next(s for s in out["patient_slots"] if s["slot_id"] == "myeongni_ref")
    assert "甲" in mye["body_markdown"]
    assert "丙寅" in mye["body_markdown"]
    assert "reports/myeongni_stub.json" in mye["body_markdown"]


@pytest.mark.skipif(not APPLY.is_file(), reason="apply script missing")
def test_apply_templates_myeongni_json(tmp_path: Path) -> None:
    bundle_in = tmp_path / "in.json"
    bundle_out = tmp_path / "out.json"
    mye_path = tmp_path / "mye.json"
    src = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    for s in src["patient_slots"]:
        if s["slot_id"] == "myeongni_ref":
            s["body_markdown"] = ""
    bundle_in.write_text(json.dumps(src, ensure_ascii=False, indent=2), encoding="utf-8")
    mye_path.write_text(
        json.dumps(
            {
                "pillars": {"year": "A", "month": "B", "day": "C", "hour": "D"},
                "day_master": {"stem_hangul": "戊"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        str(APPLY),
        "--bundle-in",
        str(bundle_in),
        "--bundle-out",
        str(bundle_out),
        "--myeongni-json",
        str(mye_path),
        "--myeongni-report-rel",
        "vault/myeongni_full.json",
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(bundle_out.read_text(encoding="utf-8"))
    mye = next(s for s in out["patient_slots"] if s["slot_id"] == "myeongni_ref")
    assert "戊" in mye["body_markdown"]
    assert "vault/myeongni_full.json" in mye["body_markdown"]


@pytest.mark.skipif(not VALIDATE.is_file(), reason="validate script missing")
def test_validate_policy_passes_minimal(tmp_path: Path) -> None:
    b = tmp_path / "b.json"
    shutil.copy(MINIMAL, b)
    cmd = [sys.executable, str(VALIDATE), "--bundle-json", str(b), "--policy-json", str(POLICY)]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout


@pytest.mark.skipif(not VALIDATE.is_file(), reason="validate script missing")
def test_validate_policy_fails_on_forbidden_substring(tmp_path: Path) -> None:
    doc = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    doc["clinical_soap_v1"]["subjective"]["text"] = "명리 때문에 통증이 생겼다고 생각합니다."
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd = [sys.executable, str(VALIDATE), "--bundle-json", str(p), "--policy-json", str(POLICY)]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 1


@pytest.mark.skipif(not VALIDATE.is_file(), reason="validate script missing")
def test_validate_policy_fails_missing_hypo_on_myeongni_slot(tmp_path: Path) -> None:
    doc = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    for s in doc["patient_slots"]:
        if s["slot_id"] == "myeongni_ref":
            s["body_markdown"] = "세운 표만 참고하세요."
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd = [sys.executable, str(VALIDATE), "--bundle-json", str(p), "--policy-json", str(POLICY)]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 1


@pytest.mark.skipif(not VALIDATE.is_file(), reason="validate script missing")
def test_validate_policy_fails_logos_included_without_non_gating(tmp_path: Path) -> None:
    doc = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    for s in doc["patient_slots"]:
        if s["slot_id"] == "logos_opt":
            s["included"] = True
            s["body_markdown"] = "짧은 상징적 해설만 적습니다."
    p = tmp_path / "bad_logos.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd = [sys.executable, str(VALIDATE), "--bundle-json", str(p), "--policy-json", str(POLICY)]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 1
    assert "[NON_GATING]" in cp.stderr or "logos" in cp.stderr.lower()


@pytest.mark.skipif(not RENDER.is_file(), reason="render script missing")
def test_render_markdown_cli(tmp_path: Path) -> None:
    out_md = tmp_path / "out.md"
    cmd = [
        sys.executable,
        str(RENDER),
        "--bundle-json",
        str(MINIMAL),
        "--out-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    text = out_md.read_text(encoding="utf-8")
    assert "# 환자 안내 번들" in text
    assert "## SOAP" in text or "SOAP (임상 기록 요약)" in text
    assert "진료 요약 및 생활 안내" in text or "core" in text


def test_render_markdown_importable() -> None:
    if not RENDER.is_file():
        pytest.skip("render script missing")
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_patient_care_bundle_md_v1", RENDER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = json.loads(MINIMAL.read_text(encoding="utf-8-sig"))
    md = mod.render_bundle_markdown(doc)
    assert "bundle_id" in md
    assert "[HYPO]" in md or "명리" in md
