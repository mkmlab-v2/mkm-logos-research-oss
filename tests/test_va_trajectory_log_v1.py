from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_va_trajectory_example_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = ROOT / "docs/final/schemas/va_trajectory_log_v1.schema.json"
    example_path = ROOT / "docs/final/schemas/va_trajectory_log_v1.example.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    instance = json.loads(example_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)


def test_build_lens_emotion_va_trajectory_ema_math():
    from scripts.build_lens_emotion_va_trajectory_v1 import build_trajectory_row

    row, _ = build_trajectory_row(
        session_id="t",
        turn_index=3,
        target_valence=0.5,
        target_arousal=0.8,
        prev_state={
            "schema": "lens_emotion_va_trajectory_state_v1",
            "current_va": {"valence": -0.2, "arousal": -0.4},
        },
        ema_alpha=0.3,
        sasang_base="soeumin",
        status="TRACKING_ACTIVE",
        note="unit",
    )
    assert row["trajectory"]["current_va"]["valence"] == pytest.approx(0.01, abs=1e-9)
    assert row["trajectory"]["current_va"]["arousal"] == pytest.approx(-0.04, abs=1e-9)


def test_cli_writes_valid_json(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "va_trajectory_log_latest.json"
    state = tmp_path / "state.json"
    cooldown_out = tmp_path / "va_cooldown_event_log_latest.json"
    schema = json.loads((ROOT / "docs/final/schemas/va_trajectory_log_v1.schema.json").read_text(encoding="utf-8"))
    ev_schema = json.loads((ROOT / "docs/final/schemas/va_cooldown_event_v1.schema.json").read_text(encoding="utf-8"))
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_emotion_va_trajectory_v1.py"),
            "--session-id",
            "pytest_sess",
            "--turn-index",
            "0",
            "--ema-alpha",
            "0.3",
            "--target-valence",
            "0.5",
            "--target-arousal",
            "0.8",
            "--state-json",
            str(state),
            "--out",
            str(out),
            "--cooldown-event-out",
            str(cooldown_out),
            "--note",
            "pytest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert r.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    ev = json.loads(cooldown_out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=ev, schema=ev_schema)
    assert ev["applied"] is False
    assert ev["reasons"] == []


def test_cli_cooldown_applies_and_writes_event(tmp_path: Path):
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "va_trajectory_log_latest.json"
    state = tmp_path / "state.json"
    event = tmp_path / "cooldown_event.json"
    schema = json.loads((ROOT / "docs/final/schemas/va_trajectory_log_v1.schema.json").read_text(encoding="utf-8"))
    event_schema = json.loads(
        (ROOT / "docs/final/schemas/va_cooldown_event_v1.schema.json").read_text(encoding="utf-8")
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_emotion_va_trajectory_v1.py"),
            "--session-id",
            "pytest_sess",
            "--turn-index",
            "1",
            "--ema-alpha",
            "1.0",
            "--target-valence",
            "-0.95",
            "--target-arousal",
            "0.98",
            "--enable-cooldown",
            "--state-json",
            str(state),
            "--out",
            str(out),
            "--cooldown-event-out",
            str(event),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["status"] == "COOLDOWN_ACTIVE"
    assert doc["cooldown_control"]["applied"] is True
    assert doc["trajectory"]["current_va"]["arousal"] < 0.98

    ev = json.loads(event.read_text(encoding="utf-8"))
    jsonschema.validate(instance=ev, schema=event_schema)
    assert ev["applied"] is True
