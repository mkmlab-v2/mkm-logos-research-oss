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
    assert doc["version"] == "1.7.0"
    syn = doc.get("synthesis_v1") or {}
    assert len(syn.get("how_to_synthesize_ko", "")) >= 80
    assert "force_hold" in syn.get("disagreement_protocol_ko", "")
    for s in doc["sections"]:
        assert len(s.get("interpretive_depth_ko", "")) >= 60
    ids = {s["axis_id"] for s in doc["sections"]}
    assert "regime_mkm_split_v1" in ids
    byeong = next(s for s in doc["sections"] if s["axis_id"] == "byeongjeung_yakri")
    sw = byeong.get("symptom_weights_v1") or {}
    assert sw.get("schema") == "sasang_byeongjeung_symptom_weights_v1"
    assert sw.get("auto_clinical_trigger") is False
    ptr = byeong.get("pyobyeong_dr_pointer_v1") or {}
    if ptr.get("present"):
        assert ptr.get("send_gate") == "HOLD"
        assert ptr.get("auto_clinical_trigger") is False
        assert "IC-08" in (ptr.get("highlight_card_ids") or [])
        assert "IC-09" in (ptr.get("highlight_card_ids") or [])
    assert "jeongchung" in (sw.get("by_constitution", {}).get("taeeum_in", {}).get("weights") or {})
    assert "persona_diary_myeongni_sasang_lane" in ids
    assert "sasang_persona_grid_v1" in ids
    assert "sasang_reading_anchor_v1" in ids
    grid_sec = next(s for s in doc["sections"] if s["axis_id"] == "sasang_persona_grid_v1")
    ptr = grid_sec.get("persona_grid_pointer") or {}
    assert ptr.get("cell_count") == 12
    assert "fabba_sidecar_ngram_lut" in ids
    fabba = next(s for s in doc["sections"] if s["axis_id"] == "fabba_sidecar_ngram_lut")
    ptr = fabba.get("shadow_metrics_pointer") or {}
    if ptr.get("present"):
        assert ptr.get("vote_participation") == "none"
        assert ptr.get("non_gating") is True


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
