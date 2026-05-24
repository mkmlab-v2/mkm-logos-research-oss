"""Smoke tests for build_family_anchor_insight_bridge_v1.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_family_anchor_insight_bridge_v1.py"
BRIDGE_SCHEMA = ROOT / "docs/final/schemas/semantic_rag_bridge_insight_bundle_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_family_anchor_bridge_cli(tmp_path: Path) -> None:
    bridge = tmp_path / "bridge.json"
    envelope = tmp_path / "envelope.json"
    one_q = tmp_path / "one_q.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--bridge-out",
            str(bridge),
            "--envelope-out",
            str(envelope),
            "--one-question-out",
            str(one_q),
            "--strict-schema",
        ],
        cwd=ROOT,
        check=True,
    )
    doc = json.loads(bridge.read_text(encoding="utf-8"))
    schema = json.loads(BRIDGE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert doc["calibration_reference"]["kind"] == "family_anchor_lived_calibration_v1"
    env = json.loads(envelope.read_text(encoding="utf-8"))
    assert env["schema"] == "three_lens_sphere_envelope_v1"
    assert env["profile_mode"] == "family_anchor"
    assert env["lenses"]["myeongni"]["available"] is True
    assert env["final_action"] == "WATCH"
    oq = json.loads(one_q.read_text(encoding="utf-8"))
    assert oq["schema"] == "family_anchor_one_question_context_v1"
