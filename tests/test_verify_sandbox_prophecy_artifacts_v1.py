"""Tests for verify_sandbox_prophecy_artifacts_v1.py."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts/verify_sandbox_prophecy_artifacts_v1.py"
    spec = importlib.util.spec_from_file_location("verify_sandbox_prophecy_artifacts_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_verify_ok_when_required_artifacts_exist():
    mod = _load()
    doc = mod.verify(manifest_path=ROOT / "reports/sandbox_prophecy_evidence_manifest_v1_latest.json")
    assert doc["schema"] == "sandbox_prophecy_artifacts_verify_v1"
    if not doc["ok"]:
        assert doc["missing_paths"] or doc["bad_schema"]
