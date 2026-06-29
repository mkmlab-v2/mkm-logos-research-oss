"""Tests for MusicGen numeric conditioning + dynamic BGM diff (B-track [HYPO])."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_clamp_tempo_for_lens_gate_low_hp():
    from scripts.audio.musicgen_numeric_conditioning_v1 import clamp_tempo_for_lens_gate

    clamped, meta = clamp_tempo_for_lens_gate(105.22)
    assert meta["lens_safe_clamp_applied"] is True
    assert clamped <= 102.28
    assert clamped >= 80.0


def test_build_dynamic_diff_hp020_applies_lens_clamp():
    from scripts.build_dynamic_bgm_conditioning_diff_v1 import build_dynamic_diff

    base = {
        "schema": "sasang_music_conditioning_v1",
        "conditioning": {"tempo_bpm_target": 96.0, "velocity_0_1": 0.45, "prompt_en": "bed calm"},
        "upstream": {"sasang_primary": "soyang"},
        "provenance": {"experiment_id": "seed"},
    }
    diff = build_dynamic_diff(base_conditioning=base, hp_pct=0.2, sasang="soyang")
    tempo = diff["suggested_conditioning_patch"]["tempo_bpm_target"]
    assert diff["lens_safe_tempo_clamp"]["lens_safe_clamp_applied"] is True
    assert tempo <= 102.28
    assert diff["inputs"]["mood"] == "urgent"


def test_build_melody_guide_mono_has_beats():
    from scripts.audio.musicgen_numeric_conditioning_v1 import build_melody_guide_mono

    guide = build_melody_guide_mono(tempo_bpm=120.0, duration_seconds=2.0, sample_rate=32000, root_pc=0)
    assert guide.shape[0] == 64000
    assert float(np.max(np.abs(guide))) <= 0.36


def test_guidance_scale_from_velocity():
    from scripts.audio.musicgen_numeric_conditioning_v1 import guidance_scale_from_velocity

    assert guidance_scale_from_velocity(None) == 3.0
    assert guidance_scale_from_velocity(0.0) == 1.5
    assert guidance_scale_from_velocity(1.0) == 5.0


def test_time_stretch_to_target_bpm_click_track(tmp_path):
    from scripts.audio.detect_bpm_v1 import measure_bpm_v1
    from scripts.audio.musicgen_numeric_conditioning_v1 import time_stretch_to_target_bpm
    from tests.test_audio_bgm_gate_report_v1 import _write_click_wav

    wav = tmp_path / "click.wav"
    _write_click_wav(wav, bpm=120.0, seconds=4.0, sample_rate=48000)
    import wave
    import struct

    with wave.open(str(wav), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    samples = [struct.unpack_from("<h", raw, i * 2)[0] / 32768.0 for i in range(len(raw) // 2)]
    stretched, meta = time_stretch_to_target_bpm(np.asarray(samples, dtype=np.float32), 48000, 96.0)
    assert meta is not None
    if meta.get("applied"):
        obs, conf = measure_bpm_v1(stretched.tolist(), 48000)
        assert obs is not None
        assert conf >= 0.25


def test_musicgen_dry_run_reports_numeric_mode():
    import subprocess
    import sys

    seed = ROOT / "data/audio/seeds/tension_sasang_01.example.json"
    cond = ROOT / "docs/final/schemas/sasang_music_conditioning_v1.example.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/audio/musicgen_external_generator_v1.py"),
            "--seed-json",
            str(seed),
            "--conditioning-json",
            str(cond),
            "--out-wav",
            str(ROOT / "reports/tmp_musicgen_dry.wav"),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["numeric_mode"] == "off"
    assert payload["numeric_fields"]["tempo_bpm_target"] == 72


def test_build_dynamic_bgm_conditioning_diff_v1():
    from scripts.build_dynamic_bgm_conditioning_diff_v1 import apply_patch_to_conditioning, build_dynamic_diff

    base = json.loads((ROOT / "docs/final/schemas/sasang_music_conditioning_v1.example.json").read_text(encoding="utf-8"))
    low_hp = build_dynamic_diff(base_conditioning=base, hp_pct=0.15, sasang="soyang")
    high_hp = build_dynamic_diff(base_conditioning=base, hp_pct=0.95, sasang="soyang")
    assert low_hp["inputs"]["mood"] == "urgent"
    assert high_hp["inputs"]["mood"] == "calm"
    assert low_hp["suggested_conditioning_patch"]["tempo_bpm_target"] > high_hp["suggested_conditioning_patch"]["tempo_bpm_target"]
    merged = apply_patch_to_conditioning(base, low_hp)
    assert merged["conditioning"]["tempo_bpm_target"] == low_hp["suggested_conditioning_patch"]["tempo_bpm_target"]


def test_run_dynamic_bgm_melody_chain_dry_run_plan():
    import subprocess
    import sys

    seed = ROOT / "data/audio/seeds/tension_sasang_01.example.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_dynamic_bgm_melody_chain_v1.py"),
            "--seed-json",
            str(seed),
            "--hp-pct",
            "0.85",
            "--sasang",
            "soyang",
            "--dry-run-plan",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload.get("ok") is True
    assert "dry_run_plan" in payload


def test_hp_sweep_conditioning_only(tmp_path):
    import subprocess
    import sys

    seed = ROOT / "data/audio/seeds/tension_sasang_01.example.json"
    out = tmp_path / "sweep"
    export = tmp_path / "sweep.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_dynamic_bgm_hp_sweep_v1.py"),
            "--seed-json",
            str(seed),
            "--hp-values",
            "0.2,1.0",
            "--output-dir",
            str(out),
            "--export-json",
            str(export),
            "--conditioning-only",
            "--no-import-known",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    doc = json.loads(export.read_text(encoding="utf-8"))
    assert doc["schema"] == "dynamic_bgm_hp_sweep_v1"
    assert len(doc["rows"]) == 2
    assert doc["rows"][0]["tempo_bpm_target"] > doc["rows"][1]["tempo_bpm_target"]


def test_lens_count_grid_conditioning_only(tmp_path):
    import subprocess
    import sys

    seed = ROOT / "data/audio/seeds/tension_sasang_01.example.json"
    out = tmp_path / "grid"
    export = tmp_path / "sweep.json"
    grid = tmp_path / "grid.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_dynamic_bgm_hp_sweep_v1.py"),
            "--seed-json",
            str(seed),
            "--hp-values",
            "0.5",
            "--lens-counts",
            "0,1,3",
            "--output-dir",
            str(out),
            "--export-json",
            str(export),
            "--export-grid-json",
            str(grid),
            "--conditioning-only",
            "--no-import-known",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(export.read_text(encoding="utf-8"))
    grid_doc = json.loads(grid.read_text(encoding="utf-8"))
    assert doc["summary"]["lens_count_grid"] == [0, 1, 3]
    assert grid_doc["schema"] == "dynamic_bgm_lens_count_grid_v1"
    assert len(grid_doc["rows"]) == 3
    by_lc = {r["lens_count"]: r for r in grid_doc["rows"]}
    assert by_lc[0]["active_lenses"] == []
    assert by_lc[1]["active_lenses"] == ["sasang"]
    assert by_lc[3]["active_lenses"] == ["sasang", "myeongni", "logos"]
    assert by_lc[3]["tempo_bpm_target"] >= by_lc[1]["tempo_bpm_target"]
