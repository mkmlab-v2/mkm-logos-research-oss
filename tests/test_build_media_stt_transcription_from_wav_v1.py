"""build_media_stt_transcription_from_wav_v1 — fixture replay + handoff chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_media_stt_transcription_from_wav_v1.py"
FIXTURE = ROOT / "tests/fixtures/media_stt_transcription_v1.example.json"
SCHEMA = ROOT / "docs/final/schemas/media_stt_transcription_v1.schema.json"


def test_fixture_replay_writes_transcription(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "stt.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--from-json",
            str(FIXTURE),
            "--out",
            str(out),
            "--strict-schema",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(doc)
    assert doc["schema"] == "media_stt_transcription_v1"
    assert len(doc["segments"]) >= 1
    assert doc["segments"][0]["start"]


def test_chain_handoff_from_fixture(tmp_path: Path) -> None:
    out = tmp_path / "stt.json"
    handoff_dir = tmp_path / "workers"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--from-json",
            str(FIXTURE),
            "--out",
            str(out),
            "--chain-handoff",
            "--task-id",
            "CHAIN-V2A",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["ok"] is True
    assert payload["chain_handoff"] is True

    md = ROOT / "reports/handoff_workers/HW-CHAIN-V2A-LOGOS_CLIP.md"
    assert md.is_file(), f"missing {md}"


def test_run_media_handoff_chain_fixture() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_media_handoff_chain_v1.py"),
            "--task-id",
            "CHAIN-AUTO",
            "--from-json",
            str(FIXTURE),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = ROOT / "reports/media_handoff_chain_v1_latest.json"
    assert report.is_file()
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["task_id"] == "CHAIN-AUTO"
