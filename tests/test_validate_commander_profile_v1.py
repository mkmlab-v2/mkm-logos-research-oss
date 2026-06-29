"""commander_profile_v1 validator tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_commander_profile_v1.py"
EXAMPLE = ROOT / "docs/final/artifacts/commander_profile_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/commander_profile_v1.schema.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_commander_profile", VALIDATOR)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not EXAMPLE.is_file(), reason="example profile missing")
def test_example_profile_validates() -> None:
    pytest.importorskip("jsonschema")
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    errors = mod.validate_profile_doc(doc, schema_path=SCHEMA)
    assert errors == []


@pytest.mark.skipif(not EXAMPLE.is_file(), reason="example profile missing")
def test_validate_cli_exit_zero_on_example() -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--profile", str(EXAMPLE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_policy_rejects_sasang_auto_merge() -> None:
    pytest.importorskip("jsonschema")
    if not EXAMPLE.is_file():
        pytest.skip("example profile missing")
    mod = _load_validator()
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8-sig"))
    doc["sasang_reference"]["auto_merge_with_myeongni"] = True
    errors = mod.validate_profile_doc(doc, schema_path=SCHEMA)
    assert any("auto_merge_with_myeongni" in e for e in errors)
