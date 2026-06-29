"""Narrative knowledge map bundle v1 smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("jsonschema") is None,
    reason="jsonschema not installed",
)
def test_narrative_knowledge_map_bundle_schema_and_walls() -> None:
    import jsonschema

    out = ROOT / "docs/final/artifacts/narrative_knowledge_map_bundle_v1_latest.json"
    if not out.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_narrative_knowledge_map_bundle_v1.py")],
            cwd=str(ROOT),
            timeout=60,
        )
        assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "docs/final/schemas/narrative_knowledge_map_bundle_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.validate(instance=doc, schema=schema)
    assert doc.get("prophecy_vote") == "none"
    assert doc.get("track_a_blocked") is True
    assert doc.get("send_gate") == "HOLD"
    assert len(doc.get("narrative_blocks") or []) > 0
    assert doc.get("ok") is True
    forbidden = ROOT / doc["policy"]["forbidden_config"]
    assert forbidden.is_file()
