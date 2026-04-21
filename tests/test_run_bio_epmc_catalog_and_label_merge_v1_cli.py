# @MKM12-METADATA
# Type: Logic
# Purpose: Fast CLI guard tests for run_bio_epmc_catalog_and_label_merge_v1.py (no network execution).
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_bio_epmc_catalog_and_label_merge_v1.py"


def test_apply_requires_with_sidecar() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--apply-sidecar-to-samples"],
        cwd=str(ROOT),
    )
    assert r.returncode == 2


def test_apply_requires_paths_when_enabled() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--with-sidecar", "--apply-sidecar-to-samples"],
        cwd=str(ROOT),
    )
    assert r.returncode == 2


def test_apply_mapping_coverage_bounds() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--with-sidecar",
            "--apply-sidecar-to-samples",
            "--apply-samples-csv",
            "x.csv",
            "--apply-mapping-csv",
            "y.csv",
            "--apply-mapping-coverage-min",
            "1.2",
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 1
