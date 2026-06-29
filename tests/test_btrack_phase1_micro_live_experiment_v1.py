"""Tests for B-track Phase-1 micro-live experiment scripts."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVE = ROOT / "scripts" / "apply_btrack_btc_typea_micro_live_human_approval_v1.py"
ENGINE = ROOT / "scripts" / "build_btrack_btc_typea_micro_live_engine_input_v1.py"
DIGEST = ROOT / "scripts" / "build_btrack_phase1_micro_live_evolution_digest_v1.py"
READINESS = ROOT / "scripts" / "build_btrack_phase1_micro_live_readiness_v1.py"


def test_micro_live_approval_idempotent() -> None:
    proc = subprocess.run(
        [sys.executable, str(APPROVE), "--reviewer", "commander"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr


def test_micro_live_engine_input_builds(tmp_path: Path) -> None:
    out = tmp_path / "engine.json"
    log = tmp_path / "signal.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ENGINE),
            "--out",
            str(out),
            "--signal-log",
            str(log),
            "--approve-submit",
            "--live",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["variant"] == "btrack_typea_micro_live_v1"
    assert "btrack_signal" in doc
    assert log.is_file()


def test_phase1_readiness_builds(tmp_path: Path) -> None:
    out = tmp_path / "ready.json"
    proc = subprocess.run(
        [sys.executable, str(READINESS), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode in (0, 1), proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_phase1_micro_live_readiness_v1"


def test_evolution_digest_builds(tmp_path: Path) -> None:
    out = tmp_path / "digest.json"
    proc = subprocess.run(
        [sys.executable, str(DIGEST), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_phase1_micro_live_evolution_digest_v1"
