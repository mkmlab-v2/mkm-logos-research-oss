"""Tests for LTM weekly ops gate bundle ([HYPO] / B-track)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_ltm_weekly_ops_gate_v1 import (  # noqa: E402
    verify_bench_report,
    verify_inject_contract,
)
from mkm_ltm_lane_purity_lib_v1 import load_inject_contract  # noqa: E402


def test_inject_contract_matches_lane_packs() -> None:
    contract = load_inject_contract()
    assert verify_inject_contract(contract) == []


def test_verify_bench_report_missing() -> None:
    assert verify_bench_report(ROOT / "reports/nonexistent_bench.json")


def test_weekly_gate_script_fast_skip(tmp_path: Path) -> None:
    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_ltm_weekly_ops_gate_v1.py"),
            "--skip-route-bench",
            "--skip-lane-purity",
            "--skip-p5-closure",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
