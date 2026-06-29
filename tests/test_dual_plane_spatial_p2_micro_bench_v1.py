from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/dual_plane_spatial_p2_scene_crosswalk_v1.json"
SCRIPT = ROOT / "scripts/run_dual_plane_spatial_p2_micro_bench_v1.py"


def test_hard_project_snaps_to_navigable():
    from scripts.run_dual_plane_spatial_p2_micro_bench_v1 import (
        build_allowed,
        hard_project_to_allowed,
    )

    allowed = build_allowed(8, {18, 26})
    assert hard_project_to_allowed(18, allowed, 8) in allowed


def test_run_bench_post_violation_zero():
    from scripts.run_dual_plane_spatial_p2_micro_bench_v1 import run_bench

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    report = run_bench(fixture)
    assert report["row_count"] >= 48
    assert report["metrics"]["post_project_violation_rate"] == 0.0
    assert report["metrics"]["raw_neural_violation_rate"] > 0.0
    assert report["metrics"]["collapsed_combined_score"] is None


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
