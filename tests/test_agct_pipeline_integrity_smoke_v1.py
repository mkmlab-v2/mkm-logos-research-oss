from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_PROFILE_GRID = _ROOT / "scripts" / "run_agct_adversarial_profile_grid_v1.py"
_STRESS_SCAN = _ROOT / "scripts" / "run_agct_stress_tail_transition_gate_scan_v1.py"
_WEIGHTS = _ROOT / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json"
_COHORT = _ROOT / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv"
_GENO = _ROOT / "tmp" / "bio_genotype_long_v1.csv"


def _require_readable(path: Path) -> None:
    if not path.is_file():
        pytest.skip(f"missing required file: {path}")
    if not os.access(path, os.R_OK):
        pytest.skip(f"unreadable required file: {path}")


def test_adversarial_profile_grid_smoke_json_integrity(tmp_path: Path) -> None:
    _require_readable(_PROFILE_GRID)
    _require_readable(_WEIGHTS)
    out = tmp_path / "agct_adversarial_profile_grid_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_PROFILE_GRID),
            "--weights-json",
            str(_WEIGHTS),
            "--n-samples",
            "120",
            "--seed",
            "20260505",
            "--output-json",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "agct_adversarial_profile_grid_v1"
    assert isinstance(data.get("profiles"), list) and len(data["profiles"]) == 3
    run_work = (data.get("inputs") or {}).get("run_work_dir")
    assert isinstance(run_work, str) and "agct_adversarial_profile_grid_v1" in run_work


def test_stress_tail_scan_smoke_json_integrity(tmp_path: Path) -> None:
    _require_readable(_STRESS_SCAN)
    _require_readable(_WEIGHTS)
    _require_readable(_COHORT)
    _require_readable(_GENO)
    out = tmp_path / "agct_stress_tail_scan_smoke.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_STRESS_SCAN),
            "--sigmas",
            "0.0315",
            "--trials",
            "2",
            "--seed",
            "20260505",
            "--base-weights-json",
            str(_WEIGHTS),
            "--cohort-csv",
            str(_COHORT),
            "--genotype-csv",
            str(_GENO),
            "--output-json",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("schema") == "agct_stress_tail_transition_gate_scan_v1"
    assert isinstance(data.get("rows"), list) and len(data["rows"]) == 1
    inputs = data.get("inputs") or {}
    assert isinstance(inputs.get("run_work_dir"), str) and "agct_stress_transition_scan_v1" in inputs["run_work_dir"]
    assert str(inputs.get("cohort_csv", "")).endswith("cohort_snapshot.csv")
    assert str(inputs.get("genotype_csv", "")).endswith("genotype_snapshot.csv")
