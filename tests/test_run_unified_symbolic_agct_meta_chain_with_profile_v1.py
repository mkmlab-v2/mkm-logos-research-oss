from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_unified_symbolic_agct_meta_chain_with_profile_v1.py"
COHORT = ROOT / "tests" / "fixtures" / "agct_demo_cohort_pass_v1.csv"
GENO = ROOT / "tests" / "fixtures" / "agct_demo_genotype_pass_v1.csv"
MAP_COV = ROOT / "tests" / "fixtures" / "agct_demo_mapping_coverage.json"


def test_profile_wrapper_smoke_neutral() -> None:
    profile_json = ROOT / "tmp" / "test_unified_meta_gate_profiles_v1.json"
    profile_json.parent.mkdir(parents=True, exist_ok=True)
    profile_json.write_text(
        json.dumps(
            {
                "schema": "unified_meta_gate_profiles_v1",
                "version": 1,
                "profiles": {
                    "neutral": {
                        "min_holdout_n": 1,
                        "min_holdout_accuracy": 0.5,
                        "max_generalization_gap": 0.4,
                        "max_holdout_pvalue": 0.2,
                        "symbolic_max_mean_loss": 0.08,
                        "symbolic_max_drift": 0.03,
                    }
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cohort-csv",
            str(COHORT),
            "--genotype-input-csv",
            str(GENO),
            "--mapping-coverage-report",
            str(MAP_COV),
            "--profile-json",
            str(profile_json),
            "--profile",
            "neutral",
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
