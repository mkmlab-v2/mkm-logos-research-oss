from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_lens_music_gematria_builtin_taeeum_json_stdout():
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--experiment-id",
            "pytest_builtin",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    env = json.loads(r.stdout)
    assert env["schema"] == "lens_music_gematria_v1"
    assert env["resolution"] == "builtin_sasang_table_v1"
    ro = env["resolved_outputs"]
    assert ro["tempo_bpm"]["target"] == 72.0
    assert ro["harmony"]["mode_hint"] == "minor"
    assert ro["harmony"]["root_pc"] == 0
    assert env["sasang_music_mapping_v1"]["inputs"]["sasang_primary"] == "taeeum"


def test_lens_music_gematria_mapping_json_example_file():
    ex = ROOT / "docs/final/schemas/sasang_music_mapping_v1.example.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--mapping-json",
            str(ex),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    env = json.loads(r.stdout)
    assert env["resolution"] == "explicit_mapping_document"
    assert env["resolved_outputs"]["tempo_bpm"]["target"] == 72.0


def test_lens_music_gematria_emotion_mapping_overlay_builtin():
    emo = ROOT / "docs/final/schemas/sasang_emotion_mapping_v1.example.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--emotion-mapping-json",
            str(emo),
            "--experiment-id",
            "pytest_emotion_overlay",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    env = json.loads(r.stdout)
    ov = env["emotion_va_overlay_v1"]
    assert ov["schema"] == "emotion_va_overlay_v1"
    assert ov["valence"] == 0.05
    assert ov["arousal"] == -0.45
    assert env["resolved_outputs"]["tempo_bpm"]["target"] == 72.0


def test_gematria_shift_deterministic():
    r1 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--gematria-total",
            "318",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--gematria-total",
            "318",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r1.returncode == 0 and r2.returncode == 0
    t1 = json.loads(r1.stdout)["resolved_outputs"]["tempo_bpm"]["target"]
    t2 = json.loads(r2.stdout)["resolved_outputs"]["tempo_bpm"]["target"]
    assert t1 == t2 == 77.0
