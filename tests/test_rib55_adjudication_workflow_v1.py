"""rib55 human adjudication workflow tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/final/artifacts/rib55_overlay_adjudication_record_v1.template.json"
SCHEMA = ROOT / "docs/final/schemas/rib55_overlay_adjudication_record_v1.schema.json"


def test_template_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc["decision"] == "pending"


def test_validate_pending_record_fails(tmp_path):
    rec = tmp_path / "pending.json"
    rec.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_rib55_overlay_adjudication_v1.py"),
            "--record-json",
            str(rec),
            "--out-json",
            str(tmp_path / "val.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_approved_record_validate_and_apply_dry_run(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    manifest_src = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
    if not manifest_src.is_file():
        pytest.skip("manifest missing")
    manifest = json.loads(manifest_src.read_text(encoding="utf-8"))
    if not manifest.get("coord_v2"):
        build = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_rib55_manifest_coord_v2_v1.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert build.returncode == 0, build.stderr
        manifest = json.loads(manifest_src.read_text(encoding="utf-8"))

    rec = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    rec["decision"] = "approved_education_internal"
    rec["reviewer_display"] = "test-reviewer"
    rec["signed_at_utc"] = "2026-06-15T16:00:00Z"
    for item in rec["checklist"]:
        item["passed"] = True
    rec_path = tmp_path / "approved.json"
    rec_path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(rec)

    val = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_rib55_overlay_adjudication_v1.py"),
            "--record-json",
            str(rec_path),
            "--out-json",
            str(tmp_path / "val.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert val.returncode == 0, val.stderr
    val_doc = json.loads((tmp_path / "val.json").read_text(encoding="utf-8"))
    assert val_doc["apply_allowed"] is True
    assert val_doc["send_gate_unlocked"] is False

    apply = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_rib55_overlay_adjudication_v1.py"),
            "--record-json",
            str(rec_path),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert apply.returncode == 0, apply.stderr


def test_workflow_builder_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_rib55_adjudication_workflow_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "docs/final/artifacts/rib55_adjudication_workflow_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["passive_corral"]["send_gate"] == "HOLD"
    assert doc["passive_corral"]["adjudication_auto_unlock_forbidden"] is True
