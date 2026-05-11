from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_fusion_control_integrity_example_validates_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "docs/final/schemas/fusion_control_integrity_audit_v1.schema.json").read_text(encoding="utf-8")
    )
    example = json.loads(
        (ROOT / "docs/final/schemas/fusion_control_integrity_audit_v1.example.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=example, schema=schema)


def test_build_audit_passes_on_consistent_bundle():
    from scripts.build_fusion_control_integrity_audit_v1 import build_audit

    va = json.loads((ROOT / "tests/fixtures/fusion_control_integrity_va_sample_v1.json").read_text(encoding="utf-8"))
    cd = json.loads(
        (ROOT / "tests/fixtures/fusion_control_integrity_cooldown_event_sample_v1.json").read_text(encoding="utf-8")
    )
    fu = json.loads(
        (ROOT / "tests/fixtures/fusion_control_integrity_fusion_report_sample_v1.json").read_text(encoding="utf-8")
    )
    report = build_audit(va, cd, fu)
    assert report["summary"]["all_pass"] is True


def test_cli_fails_on_turn_mismatch(tmp_path: Path):
    va = json.loads((ROOT / "tests/fixtures/fusion_control_integrity_va_sample_v1.json").read_text(encoding="utf-8"))
    cd = json.loads(
        (ROOT / "tests/fixtures/fusion_control_integrity_cooldown_event_sample_v1.json").read_text(encoding="utf-8")
    )
    fu = json.loads(
        (ROOT / "tests/fixtures/fusion_control_integrity_fusion_report_sample_v1.json").read_text(encoding="utf-8")
    )
    fu["va_snapshot"]["turn_index"] = 99
    va_p = tmp_path / "va.json"
    cd_p = tmp_path / "cd.json"
    fu_p = tmp_path / "fu.json"
    out_p = tmp_path / "audit.json"
    va_p.write_text(json.dumps(va), encoding="utf-8")
    cd_p.write_text(json.dumps(cd), encoding="utf-8")
    fu_p.write_text(json.dumps(fu), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_fusion_control_integrity_audit_v1.py"),
            "--va-trajectory-json",
            str(va_p),
            "--cooldown-event-json",
            str(cd_p),
            "--fusion-report-json",
            str(fu_p),
            "--out",
            str(out_p),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    out = json.loads(out_p.read_text(encoding="utf-8"))
    assert out["summary"]["all_pass"] is False
