from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts" / "run_agct_sasang_research_chain_v1.py"
COHORT_PASS = ROOT / "tests" / "fixtures" / "agct_demo_cohort_pass_v1.csv"
GENO_PASS = ROOT / "tests" / "fixtures" / "agct_demo_genotype_pass_v1.csv"


def test_research_chain_smoke(tmp_path: Path) -> None:
    cohort = COHORT_PASS
    mapping_cov = tmp_path / "mapping_cov.json"
    mapping_cov.write_text(
        json.dumps({"schema": "bio_paper_snp_mapping_coverage_v1", "coverage_ratio": 1.0}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    readiness = tmp_path / "readiness.json"
    agct = tmp_path / "agct.json"
    overlay = tmp_path / "overlay.json"
    runtime_stub = tmp_path / "runtime_stub.json"
    holdout = tmp_path / "holdout.json"
    r = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--cohort-csv",
            str(cohort),
            "--genotype-input-csv",
                str(GENO_PASS),
            "--mapping-coverage-report",
            str(mapping_cov),
            "--readiness-report",
            str(readiness),
            "--agct-sweep-report",
            str(agct),
            "--overlay-candidate-report",
            str(overlay),
            "--runtime-stub-report",
            str(runtime_stub),
            "--build-runtime-stub",
            "--run-holdout-eval",
            "--enforce-holdout-runtime-guard",
            "--holdout-eval-report",
            str(holdout),
            "--permutation-repeats",
            "100",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr

    ready_doc = json.loads(readiness.read_text(encoding="utf-8"))
    assert ready_doc.get("schema") == "bio_dna_promotion_readiness_v1"

    agct_doc = json.loads(agct.read_text(encoding="utf-8"))
    assert agct_doc.get("schema") == "agct_sasang_hypothesis_sweep_v1"
    assert agct_doc.get("summary", {}).get("n_hypotheses") == 24

    overlay_doc = json.loads(overlay.read_text(encoding="utf-8"))
    assert overlay_doc.get("schema") == "agct_sasang_size_overlay_candidate_v1"
    assert overlay_doc.get("governance", {}).get("research_only") is True
    runtime_doc = json.loads(runtime_stub.read_text(encoding="utf-8"))
    assert runtime_doc.get("schema") == "agct_sasang_size_overlay_runtime_stub_v1"
    assert runtime_doc.get("runtime_stub", {}).get("enabled") is False
    assert runtime_doc.get("holdout_runtime_guard_v1", {}).get("guard_pass") is False
    holdout_doc = json.loads(holdout.read_text(encoding="utf-8"))
    assert holdout_doc.get("schema") == "agct_sasang_holdout_eval_v1"
