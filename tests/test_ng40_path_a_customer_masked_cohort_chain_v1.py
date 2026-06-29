"""Smoke tests for Path A customer masked cohort chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/ng40_path_a_customer_masked_cohort_chain_v1_latest.json"


def test_path_a_customer_masked_cohort_chain_smoke() -> None:
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
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["chain_ok"] is True
    assert doc["synthetic_masked_rehearsal"] is True
    spine = doc["path_a_spine_eval"]
    assert spine["byte_exact_subset_parity"] >= 1.0
    assert spine.get("spine_byte_exact_ok") is True
