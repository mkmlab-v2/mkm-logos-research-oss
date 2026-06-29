"""Smoke: chat shim compress A/B bench CLI."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_chat_shim_compress_ab_bench_dry_run() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/run_chat_shim_compress_ab_bench_v1.py"),
            "--dry-run",
            "--max-cases",
            "3",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = ROOT / "reports/chat_shim_compress_ab_bench_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "chat_shim_compress_ab_bench_v1"
    assert doc.get("dry_run") is True


def test_chat_shim_compress_ab_bench_subset() -> None:
    tmp_out = ROOT / "reports/tmp_chat_shim_compress_ab_bench_v1_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sandbox/run_chat_shim_compress_ab_bench_v1.py"),
            "--out-json",
            str(tmp_out),
            "--max-cases",
            "5",
            "--min-raw-tokens",
            "12",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(tmp_out.read_text(encoding="utf-8"))
    assert doc.get("aggregate", {}).get("case_count", 0) >= 1
    assert "bundle_token_saving_rate" in doc.get("aggregate", {})
