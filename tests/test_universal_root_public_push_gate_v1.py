"""UR public push gate + B0 miss holdout named bench."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_universal_root_b0_miss_holdout_bench_v1.py"
CHECK_BENCH = ROOT / "scripts/check_universal_root_named_public_bench_v1.py"
PUSH_GATE = ROOT / "scripts/check_universal_root_public_push_gate_v1.py"
HOLDOUT = ROOT / "tests/fixtures/universal_root_b0_miss_holdout_bench_v1.json"
BENCH_SSOT = ROOT / "docs/final/artifacts/universal_root_named_public_bench_v1.json"


def test_bench_ssot_exists():
    doc = json.loads(BENCH_SSOT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "universal_root_named_public_bench_v1"
    assert doc["min_holdout_pairs"] >= 10


def test_build_b0_miss_holdout_bench():
    proc = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    holdout = json.loads(HOLDOUT.read_text(encoding="utf-8-sig"))
    assert holdout["schema"] == "universal_root_b0_miss_holdout_bench_v1"
    assert holdout["pair_count"] >= 10
    assert holdout["b0_hit_rate"] == 0.7804


def test_named_public_bench_check_strict_passes():
    proc = subprocess.run(
        [sys.executable, str(CHECK_BENCH), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_push_gate_substance_passes_after_bench():
    proc = subprocess.run(
        [sys.executable, str(PUSH_GATE), "--strict-substance", "--action", "export_materialize"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_push_gate_launch_fails_without_external_repro():
    proc = subprocess.run(
        [sys.executable, str(PUSH_GATE), "--strict-launch", "--action", "community_gtm_live"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    doc = json.loads(proc.stdout.strip().splitlines()[-1])
    assert doc["external_repro_count"] == 0


def test_export_materialize_blocked_without_bench(tmp_path):
    holdout_backup = HOLDOUT.read_text(encoding="utf-8") if HOLDOUT.is_file() else None
    try:
        if HOLDOUT.is_file():
            HOLDOUT.unlink()
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_mkm_universal_root_public_export_bundle_v1.py"),
                "--materialize",
                "--out-dir",
                str(tmp_path / "export-test"),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 2
        assert "public_push_gate_blocked" in proc.stdout
    finally:
        if holdout_backup is not None:
            HOLDOUT.write_text(holdout_backup, encoding="utf-8")
        elif not HOLDOUT.is_file():
            subprocess.run([sys.executable, str(BUILD)], cwd=str(ROOT), check=True)
