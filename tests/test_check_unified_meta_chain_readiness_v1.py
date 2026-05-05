from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_unified_meta_chain_readiness_v1.py"
COHORT = ROOT / "tests" / "fixtures" / "agct_demo_cohort_pass_v1.csv"
GENO = ROOT / "tests" / "fixtures" / "agct_demo_genotype_pass_v1.csv"
MAP_COV = ROOT / "tests" / "fixtures" / "agct_demo_mapping_coverage.json"
PAIRS = ROOT / "tests" / "fixtures" / "symbolic_mapping_demo_pairs_v1.jsonl"
STREAM = ROOT / "tests" / "fixtures" / "symbolic_mapping_shadow_stream_v1.jsonl"


def test_readiness_hold_on_small_holdout(tmp_path: Path) -> None:
    out = tmp_path / "ready.json"
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
            "--symbolic-pairs-jsonl",
            str(PAIRS),
            "--symbolic-stream-jsonl",
            str(STREAM),
            "--holdout-ratio",
            "0.3",
            "--min-holdout-n",
            "30",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "unified_meta_chain_readiness_v1"
    assert doc["decision"] == "HOLD_PRECHECK"


def test_readiness_go_with_lower_holdout_threshold(tmp_path: Path) -> None:
    out = tmp_path / "ready.json"
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
            "--symbolic-pairs-jsonl",
            str(PAIRS),
            "--symbolic-stream-jsonl",
            str(STREAM),
            "--holdout-ratio",
            "0.5",
            "--min-holdout-n",
            "2",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["decision"] == "GO_PRECHECK"
