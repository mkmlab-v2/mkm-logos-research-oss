"""Showroom subgraph audit slice builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_showroom_logos_subgraph_audit_slice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/showroom_logos_subgraph_audit_slice_v1.schema.json"
SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_subgraph_audit_slice_v1.json"
)


def test_build_showroom_logos_subgraph_audit_slice_v1(tmp_path: Path):
    out = tmp_path / "slice.json"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out-json", str(out), "--no-mirror-artifact"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_logos_subgraph_audit_slice_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert doc["router_snapshot"]["path_count"] >= 1
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema = __import__("jsonschema")
    jsonschema.Draft7Validator(schema).validate(doc)
