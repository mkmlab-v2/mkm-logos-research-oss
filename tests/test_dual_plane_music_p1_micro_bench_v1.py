from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dual_plane_music_p1_harmonic_crosswalk_v1.json"
SCRIPT = ROOT / "scripts/run_dual_plane_music_p1_micro_bench_v1.py"


def test_trajectory_buffer_clamps_large_jump():
    from scripts.run_dual_plane_music_p1_micro_bench_v1 import apply_trajectory_buffer

    buffered, applied = apply_trajectory_buffer(0, 8, max_delta_pc=2)
    assert applied is True
    assert buffered == 10


def test_hard_project_snaps_to_nearest_diatonic():
    from scripts.run_dual_plane_music_p1_micro_bench_v1 import hard_project_to_allowed

    allowed = {0, 2, 4, 5, 7, 9, 11}
    assert hard_project_to_allowed(6, allowed) in allowed
    assert hard_project_to_allowed(1, allowed) in allowed


def test_run_bench_post_project_illegal_rate_zero():
    from scripts.run_dual_plane_music_p1_micro_bench_v1 import run_bench

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    report = run_bench(fixture)
    assert report["row_count"] >= 48
    assert report["metrics"]["post_project_illegal_rate"] == 0.0
    assert report["metrics"]["raw_neural_illegal_rate"] > 0.0
    assert report["metrics"]["collapsed_combined_score"] is None


def test_micro_bench_cli_includes_latency(tmp_path):
    out = tmp_path / "bench.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fixture", str(FIXTURE), "--out", str(out), "--timing-iterations", "10"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["metrics"]["bench_wall_ms_p95"] >= 0.0
    assert doc["row_count"] >= 48


def test_micro_bench_cli_exit_zero(tmp_path):
    out = tmp_path / "bench.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--fixture", str(FIXTURE), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["schema"] == "dual_plane_music_p1_micro_bench_v1"
