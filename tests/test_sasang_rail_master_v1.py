from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
MASTER_GATE = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
MASTER_CHAIN = _ROOT / "reports/sasang_rail_master_chain_v1_latest.json"
SEED_SCRIPT = _ROOT / "scripts/seed_sasang_curated_joint_dummy_fixture_v1.py"


def test_master_gate() -> None:
    if not MASTER_GATE.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_master_status") == "master_ok"
    assert gate.get("checks", {}).get("p9_gate_ok", {}).get("passed") is True
    assert gate.get("send_gate") == "HOLD"


def test_master_chain_ok() -> None:
    if not MASTER_CHAIN.is_file():
        pytest.skip("master chain missing")
    chain = json.loads(MASTER_CHAIN.read_text(encoding="utf-8-sig"))
    core = [s for s in chain.get("steps") or [] if s.get("name") in ("stack", "p6", "master_gate")]
    assert all(s.get("ok") for s in core)


def test_dummy_seed_and_apply(tmp_path: Path) -> None:
    suffix = "pytest01"
    r = subprocess.run(
        [sys.executable, str(SEED_SCRIPT), "--suffix", suffix, "--apply-promote"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    seed_report = _ROOT / "reports/sasang_curated_joint_dummy_seed_v1_latest.json"
    doc = json.loads(seed_report.read_text(encoding="utf-8-sig"))
    assert doc.get("apply_ok") is True
    bench = _ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
    text = bench.read_text(encoding="utf-8")
    assert f"dummy_sasang_rail_jsonl_{suffix}" in text
    assert f"curated_csv_pmid_DUMMYCSV{suffix}" in text
