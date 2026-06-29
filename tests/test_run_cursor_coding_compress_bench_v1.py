"""Smoke: cursor coding compress bench dry-run and backup manifest."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_poc_gate_compressible_only_saving() -> None:
    from scripts.run_cursor_coding_compress_bench_v1 import _poc_gate

    rows = [
        {"reconstruction_fidelity_jaccard": 1.0, "token_saving_rate": 0.0, "proxy_path": "gatekeeper_bypass"},
        {"reconstruction_fidelity_jaccard": 0.8, "token_saving_rate": 0.45, "proxy_path": "live_compress"},
        {"reconstruction_fidelity_jaccard": 0.82, "token_saving_rate": 0.5, "proxy_path": "live_compress"},
    ]
    ok, detail = _poc_gate(rows)
    assert ok is True
    assert detail["compressible_count"] == 2
    assert detail["min_jaccard"] == 0.8


def test_cursor_coding_bench_dry_run() -> None:
    out = ROOT / "reports/cursor_coding_compress_bench_v1_dryrun_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_cursor_coding_compress_bench_v1.py"),
            "--dry-run",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("research_only") is True
    assert doc.get("case_count", 0) >= 1


def test_backup_manifest_writes() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_local_dev_backup_manifest_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1)
    out = ROOT / "reports/local_dev_backup_manifest_latest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "local_dev_backup_manifest_v1"
    assert "secrets_policy" in doc
