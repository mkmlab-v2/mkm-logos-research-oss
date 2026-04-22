# @MKM12-METADATA
# Type: Logic
# Purpose: Validate DNA promotion readiness gate report builder.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_bio_dna_promotion_readiness_v1.py"


def test_readiness_ok_and_strict_fail(tmp_path: Path) -> None:
    cov = tmp_path / "cov.json"
    cov.write_text(
        json.dumps({"schema": "bio_paper_snp_mapping_coverage_v1", "coverage_ratio": 0.96}, ensure_ascii=False),
        encoding="utf-8",
    )
    ov = tmp_path / "ov.json"
    ov.write_text(
        json.dumps(
            {
                "schema": "bio_genotype_paper_snp_overlap_v1",
                "summary": {"rows_with_paper_snp_targets": 12, "rows_with_any_genotype_match": 3},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    out_ok = tmp_path / "ready_ok.json"
    r_ok = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mapping-coverage-report",
            str(cov),
            "--overlap-report",
            str(ov),
            "--output-json",
            str(out_ok),
        ],
        cwd=str(ROOT),
    )
    assert r_ok.returncode == 0
    ok_doc = json.loads(out_ok.read_text(encoding="utf-8"))
    assert ok_doc.get("promotion_candidate_ready") is True

    out_fail = tmp_path / "ready_fail.json"
    r_fail = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mapping-coverage-report",
            str(cov),
            "--overlap-report",
            str(ov),
            "--output-json",
            str(out_fail),
            "--min-overlap-target-rows",
            "20",
            "--strict",
        ],
        cwd=str(ROOT),
    )
    assert r_fail.returncode == 2
    fail_doc = json.loads(out_fail.read_text(encoding="utf-8"))
    assert fail_doc.get("promotion_candidate_ready") is False

