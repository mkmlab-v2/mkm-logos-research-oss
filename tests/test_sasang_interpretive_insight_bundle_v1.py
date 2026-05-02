# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    path = _ROOT / "scripts" / "build_sasang_interpretive_insight_bundle_v1.py"
    spec = importlib.util.spec_from_file_location("build_sasang_interpretive_insight_bundle_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bundle_matches_schema_and_labels():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = _ROOT / "docs/final/schemas/sasang_interpretive_insight_bundle_v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)

    mod = _load_builder()
    doc = mod.build_bundle()
    jsonschema.Draft7Validator(schema).validate(doc)

    assert doc["rail"] == "B_TRACK"
    assert doc["decision_authority"] == "human_only"
    assert doc["schema"] == "sasang_interpretive_insight_bundle_v1"
    gate = doc["human_commander_gate_v1"]
    assert gate.get("final_authority") == "human_commander"
    assert gate.get("track") == "B"
    ids = {s["axis_id"] for s in doc["sections"]}
    assert "geumhwagyoyeok" in ids and "bomyung_jiju" in ids and "prediction" in ids


def test_builder_cli_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "bundle.json"
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_sasang_interpretive_insight_bundle_v1.py"), "-o", str(out)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["rail"] == "B_TRACK"
