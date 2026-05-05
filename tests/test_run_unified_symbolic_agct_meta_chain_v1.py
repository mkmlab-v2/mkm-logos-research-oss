from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_unified_symbolic_agct_meta_chain_v1.py"
COHORT = ROOT / "tests" / "fixtures" / "agct_demo_cohort_pass_v1.csv"
GENO = ROOT / "tests" / "fixtures" / "agct_demo_genotype_pass_v1.csv"
MAP_COV = ROOT / "tests" / "fixtures" / "agct_demo_mapping_coverage.json"
PAIRS = ROOT / "tests" / "fixtures" / "symbolic_mapping_demo_pairs_v1.jsonl"
STREAM = ROOT / "tests" / "fixtures" / "symbolic_mapping_shadow_stream_v1.jsonl"


def test_run_unified_symbolic_agct_meta_chain_v1(tmp_path: Path) -> None:
    agct_runtime = tmp_path / "agct_runtime.json"
    sym_fit = tmp_path / "sym_fit.json"
    sym_gate = tmp_path / "sym_gate.json"
    meta = tmp_path / "meta.json"
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
            "--agct-runtime-stub-json",
            str(agct_runtime),
            "--symbolic-fit-json",
            str(sym_fit),
            "--symbolic-shadow-gate-json",
            str(sym_gate),
            "--unified-meta-guard-json",
            str(meta),
            "--permutation-repeats",
            "100",
            "--runtime-enabled",
            "--min-holdout-n",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    meta_doc = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_doc["schema"] == "unified_symbolic_agct_meta_guard_v1"
    assert meta_doc["decision"] in {"PASS_UNIFIED_META_GUARD", "HOLD_UNIFIED_META_GUARD"}
