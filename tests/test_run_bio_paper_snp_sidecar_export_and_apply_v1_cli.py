# @MKM12-METADATA
# Type: Logic
# Purpose: Fast CLI guard tests for run_bio_paper_snp_sidecar_export_and_apply_v1.py (no network execution).
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_bio_paper_snp_sidecar_export_and_apply_v1.py"
SIDECAR = ROOT / "docs" / "final" / "artifacts" / "bio_measured_labels_paper_snp_sidecar_v1.json"


def test_missing_samples_csv_fails_early() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skip-export",
            "--samples-csv",
            "missing_samples.csv",
            "--mapping-csv",
            "missing_mapping.csv",
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 1


def test_mapping_coverage_bounds_check() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skip-export",
            "--samples-csv",
            "x.csv",
            "--mapping-csv",
            "y.csv",
            "--mapping-coverage-min",
            "1.5",
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 1


def test_skip_export_with_missing_sidecar_fails() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--skip-export",
            "--samples-csv",
            str(ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_samples_v1.csv"),
            "--mapping-csv",
            str(ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_mapping_v1.csv"),
            "--sidecar-json",
            str(SIDECAR.with_name("missing_sidecar.json")),
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 1
