# @MKM12-METADATA
# Type: Logic
# Purpose: B-track max prophecy evolution manifest + daily chain smoke (offline).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
MAX_PACK = _ROOT / "tests/fixtures/general_prophecy_registry_max_evolution_pack_v1.json"
SCHEMA = _ROOT / "docs/final/schemas/btrack_max_prophecy_evolution_manifest_v1.schema.json"


def test_max_evolution_pack_validates_against_general_prophecy_schema() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/generate_general_prophecy_v1.py"),
            "--dry-run",
            "--no-default-merge",
            "--input",
            str(MAX_PACK),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "24" in r.stdout


def test_max_evolution_pack_question_count() -> None:
    doc = json.loads(MAX_PACK.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_registry_v1"
    assert len(doc["questions"]) == 24
    ids = [q["question_id"] for q in doc["questions"]]
    assert len(ids) == len(set(ids))


def test_build_max_evolution_manifest_after_generate() -> None:
    gen = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/generate_general_prophecy_v1.py"),
            "--output",
            "docs/final/artifacts/general_prophecy_latest.json",
            "--stub-forecasts",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert gen.returncode == 0, gen.stderr

    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_btrack_max_prophecy_evolution_manifest_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    out = _ROOT / "docs/final/artifacts/btrack_max_prophecy_evolution_manifest_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["research_mode"] == "max_b_track"
    assert doc["send_gate"] == "HOLD"
    assert doc["question_counts"]["total"] >= 41


def test_max_prophecy_evolution_daily_chain_smoke() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/run_btrack_max_prophecy_evolution_daily_chain_v1.py"),
            "--skip-watchdog",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=170,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    report = _ROOT / "reports/btrack_max_prophecy_evolution_daily_chain_v1_latest.json"
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
