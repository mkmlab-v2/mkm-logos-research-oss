"""Smoke tests for LTM orchestration bench bundle ([HYPO] / B-track)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "reports/mkm_ltm_orchestration_bench_v1_latest.json"
CAP = ROOT / "reports/mkm_ltm_insight_cap_ablation_bench_v1_latest.json"
BUNDLE = ROOT / "reports/mkm_ltm_orchestration_bench_bundle_v1_latest.json"
PRIOR = ROOT / "docs/research/nextgen_ltm_knowledge_os/PRIOR_ART_SEARCH_LOG.jsonl"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"


@pytest.mark.skipif(not ROUTER.is_file(), reason="router sidecar missing")
def test_insight_cap_ablation_bench_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_ltm_insight_cap_ablation_bench_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(CAP.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_ltm_insight_cap_ablation_bench_v1"
    profiles = doc["profiles"]
    assert "baseline_production" in profiles
    assert int(profiles["ultra_min"]["tokens"]) <= int(profiles["baseline_production"]["tokens"])


def test_prior_art_log_seed_and_validate() -> None:
    seed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/append_mkm_prior_art_search_log_v1.py"),
            "--seed-template",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert seed.returncode == 0, seed.stderr + seed.stdout
    val = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/append_mkm_prior_art_search_log_v1.py"),
            "--validate-only",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert val.returncode == 0, val.stderr + val.stdout
    rows = [ln for ln in PRIOR.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 4


@pytest.mark.skipif(not ROUTER.is_file(), reason="router sidecar missing")
def test_orchestration_bench_bundle_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["steps"]["cap_ablation_bench"]["ok"] is True
    assert doc["steps"]["gold_query_eval"]["ok"] is True
    assert doc["steps"]["cap_gold_regression"]["ok"] is True


@pytest.mark.skipif(not ROUTER.is_file(), reason="router sidecar missing")
def test_cap_gold_regression_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_ltm_insight_cap_gold_regression_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    out = ROOT / "reports/mkm_ltm_insight_cap_gold_regression_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_ltm_insight_cap_gold_regression_v1"
    assert doc["evaluated_count"] >= 1
    assert doc["aggregate"]["best_cap_profile_under_gold_guard"]
