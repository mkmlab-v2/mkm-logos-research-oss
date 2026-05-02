# @MKM12-METADATA
# Type: Logic
# Purpose: Track B deep fusion job v1 skeleton regression.
# Keywords: logos, track_b, deep_fusion

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "run_logos_track_b_deep_fusion_job_v1.py"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_track_b_deep_fusion_job_v1.schema.json"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_TRACK_B_DEEP_FUSION_JOB_V1_CONTRACT.json"


def test_contract_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()


def test_job_runs_with_readiness_ok(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "job.json"
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--output", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("non_gating_ack") is True
    assert doc.get("execution", {}).get("llm_invoked") is False
    assert doc.get("readiness", {}).get("overall_ok") is True


def test_job_blocked_when_readiness_false(tmp_path: Path) -> None:
    bad = tmp_path / "bad_readiness.json"
    bad.write_text(
        json.dumps(
            {
                "schema": "logos_track_b_policy_readiness_v1",
                "version": "1.0.0",
                "ts_utc": "2026-01-01T00:00:00Z",
                "hypothesis_tier": "B",
                "overall_ok": False,
                "checks": {},
                "failure_codes": ["test"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "job2.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_RUNNER),
            "--readiness",
            str(bad),
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 3
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["execution"]["status"] == "blocked_readiness"
