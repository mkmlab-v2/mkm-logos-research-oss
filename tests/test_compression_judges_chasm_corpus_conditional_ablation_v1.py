"""Smoke tests for Judges/chasm corpus conditional ablation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/compression_judges_chasm_corpus_conditional_ablation_v1_latest.json"


def test_judges_chasm_ablation_smoke() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_ng40_path_a_customer_masked_cohort_chain_v1.py",
            "--rows",
            "25",
            "--skip-roi-chain",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr

    proc2 = subprocess.run(
        [sys.executable, "scripts/run_compression_judges_chasm_corpus_conditional_ablation_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc2.returncode == 0, proc2.stderr
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_judges_chasm_corpus_conditional_ablation_v1"
    assert doc["apply_active_forbidden"] is True
    assert doc["policy_counts"].get("spine_binary_chasm", 0) >= 1
    assert doc["policy_counts"].get("economy_token_proxy", 0) >= 1


def test_phase8_chain_smoke() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_ng40_dr_phase8_customer_judges_completion_chain_v1.py",
            "--skip-pytest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=360,
    )
    assert proc.returncode == 0, proc.stderr
    chain = ROOT / "reports/ng40_dr_phase8_customer_judges_completion_chain_v1_latest.json"
    assert chain.is_file()
    doc = json.loads(chain.read_text(encoding="utf-8"))
    assert doc["chain_ok"] is True
