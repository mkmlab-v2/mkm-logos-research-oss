"""B-track: VA trajectory → cross-lens fusion → integrity audit (subprocess chain smoke)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_va_fusion_control_integrity_chain_all_pass(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    state = tmp_path / "state.json"
    va_out = tmp_path / "va_trajectory_log_latest.json"
    cd_out = tmp_path / "va_cooldown_event_log_latest.json"
    fusion_out = tmp_path / "cross_lens_fusion_report_latest.json"
    audit_out = tmp_path / "fusion_control_integrity_audit_latest.json"
    stub = ROOT / "tests/fixtures/cross_lens_fusion_candidates_sample_v1.json"
    audit_schema = json.loads(
        (ROOT / "docs/final/schemas/fusion_control_integrity_audit_v1.schema.json").read_text(encoding="utf-8")
    )

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_emotion_va_trajectory_v1.py"),
            "--session-id",
            "chain_smoke_sess",
            "--turn-index",
            "0",
            "--ema-alpha",
            "0.35",
            "--target-valence",
            "0.1",
            "--target-arousal",
            "0.25",
            "--state-json",
            str(state),
            "--out",
            str(va_out),
            "--cooldown-event-out",
            str(cd_out),
            "--no-write-state",
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_cross_lens_fusion_report_v1.py"),
            "--va-trajectory-json",
            str(va_out),
            "--candidates-stub-json",
            str(stub),
            "--out",
            str(fusion_out),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_fusion_control_integrity_audit_v1.py"),
            "--va-trajectory-json",
            str(va_out),
            "--cooldown-event-json",
            str(cd_out),
            "--fusion-report-json",
            str(fusion_out),
            "--out",
            str(audit_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    audit = json.loads(audit_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=audit, schema=audit_schema)
    assert audit["summary"]["all_pass"] is True
