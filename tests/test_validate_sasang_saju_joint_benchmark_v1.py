# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "validate_sasang_saju_joint_benchmark_jsonl_v1.py"


def test_validate_passes_on_fixture(tmp_path):
    good = {
        "schema": "sasang_saju_joint_benchmark_row_v1",
        "person_id": "p1",
        "benchmark_tier": "t",
        "privacy_tier": "p",
        "provenance": "x",
        "birth_resolution": None,
    }
    pth = tmp_path / "b.jsonl"
    pth.write_text(json.dumps(good, ensure_ascii=False) + "\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--path", str(pth)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_validate_fails_bad_iso(tmp_path):
    bad = {
        "schema": "sasang_saju_joint_benchmark_row_v1",
        "person_id": "p1",
        "benchmark_tier": "t",
        "privacy_tier": "p",
        "provenance": "x",
        "birth_resolution": {"birth_instant_utc": "1990-01-01", "iana_tz": "UTC", "is_male": True},
    }
    pth = tmp_path / "b.jsonl"
    pth.write_text(json.dumps(bad, ensure_ascii=False) + "\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--path", str(pth)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stderr + r.stdout


def test_smoke_on_default_dataset():
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_sasang_saju_joint_benchmark_smoke_v1.py"),
            "--dataset",
            str(_ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_v1.jsonl"),
            "--out",
            str(_ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_smoke_v1.json"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_validate_default_repo_joint_file():
    r = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
