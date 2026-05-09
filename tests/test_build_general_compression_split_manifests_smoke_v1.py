"""Smoke: split -> split manifest builder writes train/holdout JSON (isolated tmp split root)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_split_then_manifests_in_tmp(tmp_path: Path) -> None:
    split_root = tmp_path / "splits"
    report = tmp_path / "split_report.json"
    train_m = tmp_path / "manifest_train.json"
    hold_m = tmp_path / "manifest_holdout.json"

    sp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "split_general_compression_holdout_v1.py"),
            "--out-root",
            str(split_root),
            "--holdout-ratio",
            "0.2",
            "--seed",
            "42",
            "--report",
            str(report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert sp.returncode == 0, sp.stderr + sp.stdout

    bp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_general_compression_split_manifests_v1.py"),
            "--report",
            str(report),
            "--train-out",
            str(train_m),
            "--holdout-out",
            str(hold_m),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert bp.returncode == 0, bp.stderr + bp.stdout

    assert train_m.is_file() and hold_m.is_file()
    tr = json.loads(train_m.read_text(encoding="utf-8"))
    ho = json.loads(hold_m.read_text(encoding="utf-8"))
    assert tr.get("split_role") == "train"
    assert ho.get("split_role") == "holdout"
    assert tr.get("split_key") == ho.get("split_key")
