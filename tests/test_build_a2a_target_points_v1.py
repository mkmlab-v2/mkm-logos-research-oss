"""build_a2a_target_points_v1 contract smoke."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from scripts.build_a2a_target_points_v1 import build_document

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/a2a_target_points_v1.schema.json"


def test_build_document_matches_schema():
    doc = build_document(include_kpi_snapshot=False)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["status"] == "PILOT_ALL_THREE_TP"
    assert len(doc["target_points"]) == 3
    ids = {tp["id"] for tp in doc["target_points"]}
    assert ids == {
        "tp01_cursor_ops_resume_handoff",
        "tp02_btrack_prophecy_executor_wire",
        "tp03_trackc_multilens_chain_refs",
    }


def test_emit_script_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "a2a_target_points_v1_latest.json"
    monkeypatch.setattr(
        "scripts.build_a2a_target_points_v1.DEFAULT_OUT",
        out,
    )
    monkeypatch.setattr(
        "sys.argv",
        ["build_a2a_target_points_v1.py", "--out", str(out), "--skip-kpi-snapshot"],
    )
    from scripts.build_a2a_target_points_v1 import main

    assert main() == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("schema") == "a2a_target_points_v1"
    assert payload["compress_skip_rules_v1"]["min_plaintext_tokens_recommend"] == 32


def test_strict_exit_passes_on_repo_paths():
    from scripts.build_a2a_target_points_v1 import _validate_paths, build_document

    doc = build_document(include_kpi_snapshot=False)
    errors = _validate_paths(doc, root=ROOT)
    assert errors == []
