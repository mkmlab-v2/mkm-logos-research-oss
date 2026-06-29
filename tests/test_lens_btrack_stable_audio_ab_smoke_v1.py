"""Stable Audio Open lens bake + A/B smoke dry-run contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STABLE_BAKE = ROOT / "scripts/build_lens_btrack_audio_loops_stable_audio_v1.py"
AB_SMOKE = ROOT / "scripts/run_lens_btrack_audio_generator_ab_smoke_v1.py"
STABLE_GEN = ROOT / "scripts/audio/stable_audio_open_external_generator_v1.py"
SEED = ROOT / "data/audio/seeds/tension_sasang_01.example.json"


def test_stable_audio_generator_dry_run() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(STABLE_GEN),
            "--dry-run",
            "--seed-json",
            str(SEED),
            "--out-wav",
            str(ROOT / "reports/tmp_stable_audio_dry.wav"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(r.stdout.strip().splitlines()[-1])
    assert doc["ok"] is True
    assert doc["generator"] == "stable_audio_open_external_generator_v1"


def test_stable_audio_bake_dry_run_one_pair() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(STABLE_BAKE),
            "--dry-run",
            "--only-sasang",
            "taeyang",
            "--only-mode",
            "idle",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_ab_smoke_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(AB_SMOKE), "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = ROOT / "reports/track_c_audio_hook_samples_v1/ab_generator_smoke_v1/lens_btrack_audio_generator_ab_smoke_v1_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_btrack_audio_generator_ab_smoke_v1"
    assert doc["research_only"] is True
