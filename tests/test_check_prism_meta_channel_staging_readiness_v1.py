"""Smoke: Prism meta channel staging readiness gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments/no_guard_limit_test/results"


def test_staging_readiness_mechanical_strict() -> None:
    from scripts.sandbox.check_prism_meta_channel_staging_readiness_v1 import evaluate_readiness

    checklist_path = ROOT / "experiments/no_guard_limit_test/prism_meta_channel_staging_checklist_v1.json"
    checklist = json.loads(checklist_path.read_text(encoding="utf-8"))
    doc = evaluate_readiness(checklist, run_pytest=False)
    assert doc.get("schema") == "prism_meta_channel_staging_readiness_v1"
    assert doc.get("mechanical_ok") is True
    assert (doc.get("human_signoff") or {}).get("status") == "PASS"
    assert doc.get("staging_enable_ok") is True


def test_staging_invoke_ps1_status() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/Invoke-PrismMetaChannelStaging_v1.ps1"),
            "-Action",
            "Status",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "MKM_PRISM_META_CHANNEL_BTRACK" in proc.stdout


def test_staging_live_smoke_dry_run_cli() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/run_prism_meta_channel_staging_live_smoke_v1.py"),
            "--dry-run",
            "--out-json",
            str(RESULTS / "staging_live_smoke_test.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_staging_readiness_cli_strict() -> None:
    out = RESULTS / "prism_meta_channel_staging_readiness_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/check_prism_meta_channel_staging_readiness_v1.py"),
            "--strict",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_build_n40_corpus() -> None:
    out = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n40_test.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/build_cursor_coding_compress_bench_n40_v1.py"),
            "--out-jsonl",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 40
