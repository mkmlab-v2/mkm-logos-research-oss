"""Smoke: No-Guard Limit Stress Test sandbox (dry-run + guard profile contract)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/sandbox/run_no_guard_limit_stress_test_v1.py"
PROFILE = ROOT / "experiments/no_guard_limit_test/no_guard_profile_v1.json"


def test_no_guard_profile_disables_gatekeeper() -> None:
    doc = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert doc.get("gatekeeper_bypass_max_tokens") == 0
    cb = doc.get("circuit_breaker") or {}
    assert float(cb.get("min_jaccard", 1.0)) < 0


def test_no_guard_stress_dry_run() -> None:
    out = ROOT / "experiments/no_guard_limit_test/results/no_guard_stress_dryrun_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--dry-run",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
    assert doc.get("schema") == "no_guard_limit_stress_test_v1"
    assert doc.get("guards_disabled", {}).get("gatekeeper_bypass_max_tokens") == 0
    assert doc.get("case_count", 0) >= 1


def test_classify_scenario_import() -> None:
    from scripts.sandbox.run_no_guard_limit_stress_test_v1 import _classify_scenario

    assert _classify_scenario(ok=False, jaccard=None, saving=None, error="boom") == "A_physical_collapse"
    assert (
        _classify_scenario(ok=True, jaccard=0.95, saving=0.92, error=None)
        == "B_breakthrough_candidate"
    )
    assert _classify_scenario(ok=True, jaccard=0.3, saving=0.8, error=None) == "A_quality_collapse"


def test_n20_input_exists() -> None:
    path = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n20.jsonl"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 20


def test_compare_dry_run() -> None:
    out = ROOT / "experiments/no_guard_limit_test/results/compare_dryrun_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/run_no_guard_guarded_compare_v1.py"),
            "--dry-run",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("case_count") == 20
