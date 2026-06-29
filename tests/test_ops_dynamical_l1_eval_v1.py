from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/ops_dynamical_timeseries_l1_minimal_v1.jsonl"
LIB = ROOT / "scripts/ops_dynamical_bench_v1_lib.py"


def test_l1_eval_fixture_exact_match_rate():
    sys.path.insert(0, str(ROOT))
    from scripts.ops_dynamical_bench_v1_lib import eval_l1_pairs, read_jsonl

    rows = read_jsonl(FIXTURE)
    doc = eval_l1_pairs(rows, horizon_minutes=10)
    assert doc["pairs_evaluated"] == 1
    assert doc["pairs_pending_horizon"] == 1
    assert doc["metrics"]["stage_exact_match_rate"] == 1.0
    pair = doc["pairs"][0]
    assert pair["predicted_stage"] == "stress"
    assert pair["observed_stage"] == "stress"


def test_l1_eval_runner_on_fixture(tmp_path: Path):
    jsonl = tmp_path / "series.jsonl"
    jsonl.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "eval.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ops_dynamical_l1_eval_v1.py"),
            "--jsonl",
            str(jsonl),
            "--out",
            str(out),
            "--no-patch-bench-latest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ops_dynamical_l1_eval_v1"
    assert doc["pairs_evaluated"] == 1


def test_bench_appends_jsonl(tmp_path: Path):
    jsonl = tmp_path / "series.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ops_dynamical_bench_v1.py"),
            "--jsonl",
            str(jsonl),
            "--out",
            str(tmp_path / "bench.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    lines = [ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["schema"] == "ops_dynamical_timeseries_row_v1"
