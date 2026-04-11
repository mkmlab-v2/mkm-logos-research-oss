# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke subprocess for general prophecy CLI (no network).

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_generate_general_prophecy_dry_run_with_official_seed_merge() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "--dry-run",
            "--merge-from",
            str(_ROOT / "tests" / "fixtures" / "general_prophecy_registry_official_seed_v1.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
    assert r.stdout.strip().split()[-1] == "13"


def test_generate_general_prophecy_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"), "--dry-run"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
    # default merge: sample (1) + seed_5 (5) + brier_smoke (1) + macro_h2_2026_pack (5)
    assert r.stdout.strip().split()[-1] == "12"


def test_generate_general_prophecy_dry_run_no_default_merge() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "--dry-run",
            "--no-default-merge",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().split()[-1] == "1"


def test_eval_general_prophecy_brier_stdout_on_fixture() -> None:
    fx = _ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(fx),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "general_prophecy_brier_eval_v1" in r.stdout


def test_eval_general_prophecy_brier_on_merged_registry_stdout(tmp_path) -> None:
    import json

    gen = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "generate_general_prophecy_v1.py"),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert gen.returncode == 0, gen.stderr
    reg = json.loads(gen.stdout)
    assert reg.get("schema") == "general_prophecy_registry_v1"
    assert len(reg.get("questions") or []) == 12

    merged_path = tmp_path / "merged_registry.json"
    merged_path.write_text(gen.stdout, encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "eval_general_prophecy_brier_score.py"),
            "-i",
            str(merged_path),
            "--stdout-only",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out.get("schema") == "general_prophecy_brier_eval_v1"
    assert out.get("metrics", {}).get("n_evaluated") == 1
    assert out.get("metrics", {}).get("mean_brier_score") == 0.09
