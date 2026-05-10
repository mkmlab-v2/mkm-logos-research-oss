from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_symbolic_hold_when_velocity_over_cap():
    from scripts.run_lens_music_gematria_gate_chain_v1 import evaluate_symbolic_safety

    outputs = {
        "tempo_bpm": {"target": 72.0, "min": 60.0, "max": 84.0},
        "harmony": {"mode_hint": "minor", "root_pc": 0},
        "dynamics": {"velocity_0_1": 0.95},
        "safety": {"min_hz": 80.0, "max_hz": 12000.0, "max_velocity_0_1": 0.5},
    }
    dec, _eff, reasons, notes = evaluate_symbolic_safety(outputs, policy="hold")
    assert dec == "HOLD"
    assert any("velocity_over_cap" in r for r in reasons)
    assert not notes


def test_symbolic_clip_when_velocity_over_cap():
    from scripts.run_lens_music_gematria_gate_chain_v1 import evaluate_symbolic_safety

    outputs = {
        "tempo_bpm": {"target": 72.0, "min": 60.0, "max": 84.0},
        "harmony": {"mode_hint": "minor", "root_pc": 0},
        "dynamics": {"velocity_0_1": 0.95},
        "safety": {"min_hz": 80.0, "max_hz": 12000.0, "max_velocity_0_1": 0.5},
    }
    dec, eff, reasons, notes = evaluate_symbolic_safety(outputs, policy="clip")
    assert dec == "CLIPPED_OK"
    assert not reasons
    assert eff["dynamics"]["velocity_0_1"] == 0.5
    assert notes


def test_chain_end_to_end_subprocess(tmp_path):
    lens_out = tmp_path / "lens.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--output",
            str(lens_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr

    wav_path = tmp_path / "silence.wav"
    r_wav = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/generate_placeholder_wav.py"),
            "--out",
            str(wav_path),
            "--seconds",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r_wav.returncode == 0, r_wav.stderr

    chain_report = tmp_path / "chain.json"
    audio_report = tmp_path / "gate.json"

    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{os.pathsep}{prev}"
    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria_gate_chain_v1.py"),
            "--lens-json",
            str(lens_out),
            "--wav",
            str(wav_path),
            "--export-chain",
            str(chain_report),
            "--export-audio-report",
            str(audio_report),
            "--commercial-terms-tag",
            "apache2_self_host_weights_v1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout

    chain = json.loads(chain_report.read_text(encoding="utf-8"))
    assert chain["schema"] == "lens_music_gate_chain_v1"
    assert chain["symbolic_stage"]["decision"] == "PASS"
    assert chain["audio_gate"]["decision"] == "PASS"
    assert chain["melody_stage_m9"]["enabled"] is True
    assert chain["melody_stage_m9"]["schema"] == "melody_overlay_advisory_v1"


def test_chain_includes_emotion_overlay_when_lens_has_it(tmp_path):
    emo = ROOT / "docs/final/schemas/sasang_emotion_mapping_v1.example.json"
    lens_out = tmp_path / "lens.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--emotion-mapping-json",
            str(emo),
            "--output",
            str(lens_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr

    wav_path = tmp_path / "silence.wav"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/generate_placeholder_wav.py"),
            "--out",
            str(wav_path),
            "--seconds",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    chain_report = tmp_path / "chain.json"
    audio_report = tmp_path / "gate.json"
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{os.pathsep}{prev}"
    r2 = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria_gate_chain_v1.py"),
            "--lens-json",
            str(lens_out),
            "--wav",
            str(wav_path),
            "--export-chain",
            str(chain_report),
            "--export-audio-report",
            str(audio_report),
            "--commercial-terms-tag",
            "apache2_self_host_weights_v1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r2.returncode == 0, r2.stderr + r2.stdout

    chain = json.loads(chain_report.read_text(encoding="utf-8"))
    assert chain["emotion_va_overlay_v1"]["valence"] == 0.05
    assert chain["emotion_va_overlay_v1"]["arousal"] == -0.45


def test_chain_emotion_overlay_preview_mode_adds_stage_without_mutation(tmp_path):
    emo = ROOT / "docs/final/schemas/sasang_emotion_mapping_v1.example.json"
    lens_out = tmp_path / "lens.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--emotion-mapping-json",
            str(emo),
            "--output",
            str(lens_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    wav_path = tmp_path / "silence.wav"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/generate_placeholder_wav.py"),
            "--out",
            str(wav_path),
            "--seconds",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    chain_report = tmp_path / "chain_preview.json"
    audio_report = tmp_path / "gate_preview.json"
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{os.pathsep}{prev}"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria_gate_chain_v1.py"),
            "--lens-json",
            str(lens_out),
            "--wav",
            str(wav_path),
            "--emotion-overlay-policy",
            "preview",
            "--export-chain",
            str(chain_report),
            "--export-audio-report",
            str(audio_report),
            "--commercial-terms-tag",
            "apache2_self_host_weights_v1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    chain = json.loads(chain_report.read_text(encoding="utf-8"))
    assert chain["emotion_overlay_stage"]["policy"] == "preview"
    assert chain["emotion_overlay_stage"]["would_apply"] is False
    # preview mode keeps symbolic outputs unchanged from original taeeum target.
    assert chain["symbolic_stage"]["effective_outputs"]["tempo_bpm"]["target"] == 72.0
    assert chain["quality_guard_m7"]["enabled"] is True
    assert chain["quality_guard_m7"]["status"] == "OK"
    assert chain["quality_guard_m7"]["warn_count"] == 0


def test_chain_emotion_overlay_apply_mode_mutates_effective_outputs(tmp_path):
    emo = ROOT / "docs/final/schemas/sasang_emotion_mapping_v1.example.json"
    lens_out = tmp_path / "lens.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria.py"),
            "--sasang-primary",
            "taeeum",
            "--emotion-mapping-json",
            str(emo),
            "--output",
            str(lens_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    wav_path = tmp_path / "silence.wav"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/generate_placeholder_wav.py"),
            "--out",
            str(wav_path),
            "--seconds",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    chain_report = tmp_path / "chain_apply.json"
    audio_report = tmp_path / "gate_apply.json"
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) if not prev else f"{ROOT}{os.pathsep}{prev}"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_lens_music_gematria_gate_chain_v1.py"),
            "--lens-json",
            str(lens_out),
            "--wav",
            str(wav_path),
            "--emotion-overlay-policy",
            "apply",
            "--export-chain",
            str(chain_report),
            "--export-audio-report",
            str(audio_report),
            "--commercial-terms-tag",
            "apache2_self_host_weights_v1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    chain = json.loads(chain_report.read_text(encoding="utf-8"))
    assert chain["emotion_overlay_stage"]["policy"] == "apply"
    assert chain["emotion_overlay_stage"]["would_apply"] is True
    assert chain["symbolic_stage"]["effective_outputs"]["tempo_bpm"]["target"] < 72.0
    assert chain["quality_guard_m7"]["enabled"] is True
    assert chain["quality_guard_m7"]["status"] == "OK"
    assert chain["quality_guard_m7"]["warn_count"] == 0
    # M9 melody advisory should expose scale/pentatonic constraints.
    m9 = chain["melody_stage_m9"]
    assert m9["enabled"] is True
    assert m9["theory_suggestion"]["allow_pentatonic"] is True
    assert m9["phrase_constraints"]["max_leap_semitones"] >= 7
