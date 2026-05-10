from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_agct_sasang_holdout_eval_v1.py"
COHORT = ROOT / "tests" / "fixtures" / "agct_demo_cohort_pass_v1.csv"
GENO = ROOT / "tests" / "fixtures" / "agct_demo_genotype_pass_v1.csv"


def test_holdout_eval_smoke(tmp_path: Path) -> None:
    out = tmp_path / "holdout_eval.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cohort-csv",
            str(COHORT),
            "--genotype-csv",
            str(GENO),
            "--holdout-ratio",
            "0.5",
            "--seed",
            "7",
            "--permutation-repeats",
            "100",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "agct_sasang_holdout_eval_v1"
    assert doc["split"]["paired_samples"] == 4
    assert 0.0 <= float(doc["results"]["train_accuracy"]) <= 1.0
    assert 0.0 <= float(doc["results"]["holdout_accuracy_under_train_mapping"]) <= 1.0


def test_holdout_eval_insufficient_pairs_writes_hold(tmp_path: Path) -> None:
    """Fewer than 4 paired samples must exit 0 with HOLD artifact (daily automation friendly)."""
    cohort = tmp_path / "cohort.csv"
    cohort.write_text(
        "sample_id,expected_parent\n"
        "s1,Yang\n"
        "s2,Yin\n",
        encoding="utf-8",
    )
    geno = tmp_path / "geno.csv"
    geno.write_text(
        "sample_id,genotype\n"
        "s1,AA\n",
        encoding="utf-8",
    )
    out = tmp_path / "holdout_eval.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cohort-csv",
            str(cohort),
            "--genotype-csv",
            str(geno),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "agct_sasang_holdout_eval_v1"
    assert doc["summary"]["status"] == "INSUFFICIENT_PAIRED_SAMPLES_HOLD"
    assert doc["results"] == {}
