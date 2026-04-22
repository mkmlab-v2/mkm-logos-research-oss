# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke threshold sweep for DNA promotion readiness.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_bio_dna_promotion_threshold_sweep_v1.py"


def test_threshold_sweep_recommends_strictest_passing(tmp_path: Path) -> None:
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
                "summary": {"rows_with_paper_snp_targets": 12, "rows_with_any_genotype_match": 2},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    out = tmp_path / "sweep.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mapping-coverage-report",
            str(cov),
            "--overlap-report",
            str(ov),
            "--coverage-threshold-grid",
            "0.95,0.97",
            "--target-rows-threshold-grid",
            "10,13",
            "--match-rows-threshold-grid",
            "1,2,3",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
    )
    assert r.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "bio_dna_promotion_threshold_sweep_v1"
    assert int(doc["summary"]["candidate_count"]) == 12
    assert int(doc["summary"]["passing_count"]) == 2
    assert doc["summary"]["recommended_policy"] == {
        "min_mapping_coverage_ratio": 0.95,
        "min_overlap_target_rows": 10,
        "min_overlap_match_rows": 2,
    }

