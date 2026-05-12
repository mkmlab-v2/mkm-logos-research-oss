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
    assert doc["milestones_ack"]["M5_emotion_va_overlay"] is True
    assert doc["emotion_va_overlay_ack"]["pytest_includes_emotion_va_overlay_tests"] is True
    assert doc["emotion_va_overlay_ack"]["does_not_gate_promotion_decision"] is True
    assert "track_c_section_3_10_emotion_va" in doc["references_ssot"]
    m31 = doc.get("m31_hormone_guard") or {}
    assert "invocation" in m31
    assert m31["invocation"]["profile"] == "strict"
    assert m31["invocation"]["require_m31_input"] is True
    pp = doc.get("promotion_process") or {}
    assert pp.get("m31_profile") == "strict"
    assert pp.get("process_pass") is True
    assert pp.get("pytest_pass") is True
    assert pp.get("process_exit_code") == 0


def test_promotion_gate_process_exit_code_w4():
    import importlib.util

    script = ROOT / "scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py"
    spec = importlib.util.spec_from_file_location("_lens_music_promotion_gate_w4", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    fn = mod.promotion_gate_process_exit_code
    assert fn(1, "B_TRACK_RESEARCH_PROMOTION_READY", m31_profile="strict") == 1
    assert fn(0, "HOLD_M31_HORMONE_GUARD", m31_profile="strict") == 1
    assert fn(0, "HOLD_M31_HORMONE_GUARD", m31_profile="soft") == 0
    assert fn(0, "B_TRACK_RESEARCH_PROMOTION_READY", m31_profile="strict") == 0
    assert fn(0, "HOLD_PYTEST_FAILED", m31_profile="strict") == 0


def test_promotion_gate_m31_profile_soft_emits_invocation():
    import subprocess
    import sys

    script = ROOT / "scripts/check_lens_music_symbolic_audio_promotion_gate_v1.py"
    out_path = ROOT / "reports" / "_tmp_lens_music_promotion_gate_soft_profile.json"
    r = subprocess.run(
        [
            sys.executable,
            str(script),
            "--out",
            str(out_path),
            "--m31-profile",
            "soft",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    m31 = doc.get("m31_hormone_guard") or {}
    inv = m31.get("invocation") or {}
    assert inv.get("profile") == "soft"
    assert inv.get("require_m31_input") is False
    pp = doc.get("promotion_process") or {}
    assert pp.get("process_pass") is True
    assert pp.get("process_exit_code") == 0
