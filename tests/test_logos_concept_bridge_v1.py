"""logos_concept_bridge_v1 schema + semiconductor PoC builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_concept_bridge_v1.schema.json"
BUILDER = ROOT / "scripts/build_logos_concept_bridge_semiconductor_poc_v1.py"


def test_semiconductor_poc_matches_schema(tmp_path: Path) -> None:
    out = tmp_path / "bridge.json"
    cp = subprocess.run(
        [sys.executable, str(BUILDER), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert doc["policy"]["no_prophecy_claim"] is True
    assert "topology_overlap_percent" not in doc
    assert "prophecy_hit_rate" not in doc
    assert len(doc["paths"]) >= 3


def test_latest_artifact_if_present() -> None:
    latest = ROOT / "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json"
    if not latest.is_file():
        return
    doc = json.loads(latest.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
