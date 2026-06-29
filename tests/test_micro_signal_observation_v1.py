# @MKM12-METADATA
# Type: Logic
# Purpose: CI lock for micro_signal_observation_v1 schema and builder smoke.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "docs" / "final" / "schemas" / "micro_signal_observation_v1.schema.json"
_FIXTURE = _ROOT / "tests" / "fixtures" / "micro_signal_observation_bundle_v1.example.json"
_BUILDER = _ROOT / "scripts" / "build_micro_signal_observation_bundle_v1.py"
_VALIDATOR = _ROOT / "scripts" / "validate_micro_signal_observation_bundle_v1.py"


@pytest.fixture(scope="module")
def _validator():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_micro_signal_schema_file_exists() -> None:
    assert _SCHEMA.is_file()


def test_micro_signal_fixture_validates(_validator) -> None:
    assert _FIXTURE.is_file()
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    errs = sorted(_validator.iter_errors(doc), key=lambda e: e.path)
    assert not errs, "schema errors: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errs[:12])
    assert doc.get("fusion_forbidden_ack") is True
    assert doc.get("lens_partition_ack") is True


def test_build_micro_signal_bundle_smoke(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_BUILDER),
            "--output",
            str(out),
            "--skip-brief",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert r.returncode == 0, r.stderr
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "micro_signal_observation_bundle_v1"
    assert doc["summary"]["n_observations"] >= 5
    assert "market_ohlcv" in doc["summary"]["domains_present"]


def test_validate_micro_signal_bundle_on_fixture(tmp_path: Path) -> None:
    dst = tmp_path / "bundle.json"
    dst.write_text(_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_VALIDATOR), "--input", str(dst)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "VALIDATION_OK" in r.stdout
