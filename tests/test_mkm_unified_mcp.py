"""Smoke tests for scripts/mkm_unified_mcp.py (importorskip mcp)."""
from __future__ import annotations

import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


pytest.importorskip("mcp")


@pytest.fixture
def mod():
    os.environ["MKM_PROPHECY_REGISTRY_PATH"] = str(
        ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
    )
    spec = spec_from_file_location("mkm_unified_mcp", ROOT / "scripts" / "mkm_unified_mcp.py")
    m = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def test_registry_summary(mod):
    s = json.loads(mod.prophecy_registry_summary())
    assert s["ok"] is True
    assert s["question_count"] == 1
    assert "demo.binary.sample_01" in s["question_ids"]


def test_get_question(mod):
    q = json.loads(mod.prophecy_get_question("demo.binary.sample_01"))
    assert q["ok"] is True
    assert q["question"]["question_id"] == "demo.binary.sample_01"


def test_get_question_missing(mod):
    q = json.loads(mod.prophecy_get_question("nope"))
    assert q["ok"] is False


def test_payload_validate_ok(mod):
    payload = {
        "schema": "mkm_compressed_payload_v1",
        "payload_kind": "lossless_excerpt",
        "text_effective": "x",
        "source": {"kind": "inline"},
    }
    r = json.loads(mod.mkm_payload_validate(json.dumps(payload)))
    assert r["ok"] is True


def test_payload_validate_bad_schema(mod):
    r = json.loads(mod.mkm_payload_validate("{}"))
    assert r["ok"] is False


def test_payload_build(mod):
    r = json.loads(
        mod.mkm_payload_build(
            "hello world",
            "prophecy_brief_slice",
            "artifact_path",
            "docs/final/artifacts/general_prophecy_latest.json",
        )
    )
    assert r["ok"] is True
    assert r["payload"]["schema"] == "mkm_compressed_payload_v1"
