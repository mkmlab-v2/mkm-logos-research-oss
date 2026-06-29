"""Smoke tests for MKM bench TUI spike ([HYPO] / B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "reports/mkm_ltm_orchestration_bench_v1_latest.json"
OUT = ROOT / "reports/mkm_bench_tui_spike_v1_latest.json"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"


@pytest.mark.skipif(not ORCH.is_file(), reason="orchestration bench artifact missing")
def test_mkm_bench_tui_spike_replay_only_exit_zero() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_mkm_bench_tui_spike_v1.py"),
            "--replay-only",
            "--plain",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "mkm_bench_tui_spike_v1"
    assert doc["ok"] is True
    assert doc["ollama_required"] is False
    hero = doc["hero_metrics"]
    naive = int(hero["naive_baseline_tokens"])
    assert naive >= 50_000
    assert float(hero["shallow_mean_savings_ratio"]) >= 0.99
    assert 0.30 <= float(hero["orchestrated_savings_ratio"]) <= 0.36


@pytest.mark.skipif(not ROUTER.is_file(), reason="router sidecar missing")
def test_mkm_bench_tui_spike_full_bundle_exit_zero() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_mkm_bench_tui_spike_v1.py"),
            "--plain",
            "--skip-prior-art-seed",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["bundle_step"].get("exit_code") == 0
