# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test DNA readiness chain runner.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts" / "run_bio_dna_readiness_chain_v1.py"
APPLY = ROOT / "scripts" / "apply_bio_paper_snp_sidecar_to_samples_v1.py"
COV = ROOT / "scripts" / "check_bio_paper_snp_mapping_coverage_v1.py"
SAMPLES = ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_samples_v1.csv"
MAPPING = ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_mapping_v1.csv"
SIDECAR = ROOT / "docs" / "final" / "artifacts" / "bio_measured_labels_paper_snp_sidecar_v1.json"
GENO = ROOT / "tests" / "fixtures" / "bio_genotype_rsid_smoke_v1.csv"


def test_chain_smoke(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    subprocess.check_call(
        [
            sys.executable,
            str(APPLY),
            "--samples-csv",
            str(SAMPLES),
            "--mapping-csv",
            str(MAPPING),
            "--sidecar-json",
            str(SIDECAR),
            "--output-csv",
            str(cohort),
            "--output-report",
            str(tmp_path / "apply_report.json"),
        ],
        cwd=str(ROOT),
    )

    mapping_cov = tmp_path / "mapping_cov.json"
    subprocess.check_call(
        [
            sys.executable,
            str(COV),
            "--cohort-csv",
            str(SAMPLES),
            "--mapping-csv",
            str(MAPPING),
            "--output-json",
            str(mapping_cov),
        ],
        cwd=str(ROOT),
    )

    readiness = tmp_path / "readiness.json"
    sweep = tmp_path / "sweep.json"
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--cohort-csv",
            str(cohort),
            "--genotype-input-csv",
            str(GENO),
            "--mapping-coverage-report",
            str(mapping_cov),
            "--readiness-report",
            str(readiness),
            "--run-threshold-sweep",
            "--threshold-sweep-report",
            str(sweep),
            "--min-overlap-target-rows",
            "1",
            "--strict-readiness",
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 0
    doc = json.loads(readiness.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bio_dna_promotion_readiness_v1"
    assert isinstance(doc.get("promotion_candidate_ready"), bool)
    sweep_doc = json.loads(sweep.read_text(encoding="utf-8"))
    assert sweep_doc.get("schema") == "bio_dna_promotion_threshold_sweep_v1"

