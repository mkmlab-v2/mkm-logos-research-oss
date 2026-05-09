"""Smoke: holdout split produces train/holdout JSONL and report (tmp root)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_split_holdout_report_and_counts(tmp_path: Path) -> None:
    manifest = ROOT / "docs/final/artifacts/general_compression_benchmark_manifest_v1.json"
    out_root = tmp_path / "split_out"
    report = tmp_path / "report.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "split_general_compression_holdout_v1.py"),
        "--manifest",
        str(manifest),
        "--out-root",
        str(out_root),
        "--holdout-ratio",
        "0.2",
        "--seed",
        "42",
        "--report",
        str(report),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout

    assert report.is_file()
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc.get("schema") == "general_compression_holdout_split_report_v1"
    totals = doc.get("totals") or {}
    assert int(totals.get("train", 0)) + int(totals.get("holdout", 0)) >= 1

    train_dir = out_root / "train"
    hold_dir = out_root / "holdout"
    assert train_dir.is_dir() and hold_dir.is_dir()
    assert any(train_dir.glob("*.jsonl")) or any(hold_dir.glob("*.jsonl"))
