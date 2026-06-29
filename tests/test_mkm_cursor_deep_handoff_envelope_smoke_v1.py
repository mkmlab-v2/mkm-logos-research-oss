# Keywords: deep_handoff_envelope, ltm, resume_pack, tier3_wire

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_mkm_cursor_deep_handoff_envelope_v1.py"
SCHEMA = ROOT / "docs/final/schemas/mkm_cursor_deep_handoff_envelope_v1.schema.json"
ARTIFACT = ROOT / "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json"


def test_schema_valid():
    pytest.importorskip("jsonschema")
    from jsonschema import Draft202012Validator

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_build_envelope_infra_exit0():
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--lane",
            "infra",
            "--continuity-id",
            "p2-smoke-infra",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_cursor_deep_handoff_envelope_v1"
    assert doc["graph_axis"] == "A_ltm"
    assert doc["lane"] == "infra"
    assert doc["deep_fetch_next"]
    assert all("graph_slice" not in p.lower() for p in doc["deep_fetch_next"])
    assert "tier3_wire" in doc
    assert doc["resume_pack"]["pins"]


def test_validate_envelope_rejects_graph_slice():
    from scripts.build_mkm_cursor_deep_handoff_envelope_v1 import validate_envelope

    bad = {
        "schema": "mkm_cursor_deep_handoff_envelope_v1",
        "generated_at_utc": "2026-06-26T00:00:00Z",
        "lane": "infra",
        "graph_axis": "A_ltm",
        "research_only": True,
        "send_gate": "HOLD",
        "continuity_id": "bad",
        "resume_pack": {
            "md_path": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
            "json_path": "docs/final/artifacts/mkm_chat_resume_pack_latest.json",
            "pins": [{"node_id": "prism_ops_lane_infra"}],
        },
        "shallow_handoff": {
            "schema": "ollama_shallow_router_handoff_v1",
            "source_path": "reports/ollama_shallow_router_handoff_v1_latest.json",
        },
        "tier3_wire": {
            "index_path": "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_lane_index_v1_latest.json",
            "brief_path": "docs/final/artifacts/a2a_tier3_cursor_wire_handoff_brief_infra_v1_latest.md",
            "pilot_ok": True,
        },
        "ltm_concept_ids": ["ltm_graph_meta"],
        "deep_fetch_next": ["data/logos_studio/graph_slice_v1.json"],
        "read_order": ["a", "b"],
    }
    errs = validate_envelope(bad)
    assert any("graph_slice" in e for e in errs)
