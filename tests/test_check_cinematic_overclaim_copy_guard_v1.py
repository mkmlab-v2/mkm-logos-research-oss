from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/cinematic/check_cinematic_overclaim_copy_guard_v1.py"
SCENARIO = ROOT / "docs/final/artifacts/cinematic_scenario_v2_ko.txt"


def _run_guard(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GUARD), *[str(p) for p in paths]],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_cinematic_overclaim_guard_passes_default_scenario():
    assert SCENARIO.is_file()
    r = _run_guard(SCENARIO)
    assert r.returncode == 0, r.stderr + r.stdout


def test_cinematic_overclaim_guard_fails_hollywood_hype(tmp_path: Path):
    bad = tmp_path / "bad_scenario.txt"
    bad.write_text("노트북 한 대로 할리우드 수준 특수 효과 영상을 만든다.\n", encoding="utf-8")
    r = _run_guard(bad)
    assert r.returncode == 1
    assert "O-02" in r.stdout
