# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke genotype-vs-paper SNP overlap checker.
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_bio_genotype_paper_snp_overlap_v1.py"
APPLY = ROOT / "scripts" / "apply_bio_paper_snp_sidecar_to_samples_v1.py"
SAMPLES = ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_samples_v1.csv"
MAPPING = ROOT / "tests" / "fixtures" / "bio_paper_snp_join_smoke_mapping_v1.csv"
SIDECAR = ROOT / "docs" / "final" / "artifacts" / "bio_measured_labels_paper_snp_sidecar_v1.json"
GENO = ROOT / "tests" / "fixtures" / "bio_genotype_rsid_smoke_v1.csv"


def test_genotype_overlap_smoke(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort_rep = tmp_path / "cohort_rep.json"
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
            str(cohort_rep),
        ],
        cwd=str(ROOT),
    )

    out = tmp_path / "overlap.csv"
    rep = tmp_path / "overlap.json"
    subprocess.check_call(
        [
            sys.executable,
            str(SCRIPT),
            "--cohort-csv",
            str(cohort),
            "--genotype-csv",
            str(GENO),
            "--output-csv",
            str(out),
            "--output-report",
            str(rep),
        ],
        cwd=str(ROOT),
    )

    rows = list(csv.DictReader(io.StringIO(out.read_text(encoding="utf-8"))))
    assert len(rows) == 1
    r = rows[0]
    assert r["dna_genotype_rsid_count"] == "2"
    assert r["dna_paper_snp_target_count"] == "4"
    assert r["dna_paper_snp_match_count"] == "1"
    assert r["dna_paper_snp_matched_rsids"] == "rs10937331"
    doc = json.loads(rep.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bio_genotype_paper_snp_overlap_v1"
