from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_promotion_gate_example_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = ROOT / "docs/final/schemas/lens_music_symbolic_audio_promotion_gate_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/lens_music_symbolic_audio_promotion_gate_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_promotion_gate_script_matches_live_pytest():
    """Runs consolidated pytest via promotion gate; must match green CI bundle."""
    import subprocess
    import sys

    script = ROOT / "scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py"
    out_path = ROOT / "reports" / "_tmp_lens_music_promotion_gate_test.json"
    r = subprocess.run(
        [sys.executable, str(script), "--out", str(out_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["decision"] == "B_TRACK_RESEARCH_PROMOTION_READY"
    assert doc["track_wall"]["promotion_to_a_track_commercial_audio"] is False
    assert doc["emotion_va_overlay_ack"]["pytest_includes_emotion_va_overlay_tests"] is True
    assert doc["emotion_va_overlay_ack"]["does_not_gate_promotion_decision"] is True
    assert "track_c_section_3_10_emotion_va" in doc["references_ssot"]
