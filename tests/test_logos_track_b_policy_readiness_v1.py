# @MKM12-METADATA
# Type: Logic
# Purpose: Track B policy readiness report regression.
# Keywords: logos, track_b, readiness

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "report_logos_track_b_policy_readiness_v1.py"
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "logos_track_b_policy_readiness_v1.schema.json"
_CONTRACT = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_TRACK_B_POLICY_READINESS_V1_CONTRACT.json"
_THEOLOGY = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_MKM_THEOLOGY_BASELINE_V1.json"


def test_contract_schema_exist() -> None:
    assert _CONTRACT.is_file()
    assert _SCHEMA.is_file()


def test_runner_default_paths_exit_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--theology-baseline", str(_THEOLOGY)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out_path = _ROOT / "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"
    assert out_path.is_file()
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    assert doc.get("overall_ok") is True
