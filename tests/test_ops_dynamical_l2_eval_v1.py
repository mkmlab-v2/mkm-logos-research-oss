from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/ops_dynamical_timeseries_l2_minimal_v1.jsonl"


def test_l2_eval_fixture_equilibrium_restore():
    sys.path.insert(0, str(ROOT))
    from scripts.ops_dynamical_bench_v1_lib import eval_l2_interventions, read_jsonl

    doc = eval_l2_interventions(read_jsonl(FIXTURE))
    assert doc["pairs_evaluated"] == 1
    assert doc["metrics"]["equilibrium_restore_rate"] == 1.0
    pair = doc["pairs"][0]
    assert pair["stress_delta"] == -0.34
    assert pair["improved"] is True
    assert pair["equilibrium_restored"] is True


def test_l2_synthetic_chain(tmp_path: Path):
    jsonl = tmp_path / "series.jsonl"
    out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ops_dynamical_l2_intervention_chain_v1.py"),
            "--mode",
            "synthetic",
            "--jsonl",
            str(jsonl),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["mode"] == "synthetic"
    assert doc["l2_metrics"]["equilibrium_restore_rate"] == 1.0
    assert len([ln for ln in jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]) == 2


def test_l2_eval_runner_on_fixture(tmp_path: Path):
    jsonl = tmp_path / "series.jsonl"
    jsonl.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "eval.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ops_dynamical_l2_eval_v1.py"),
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
    assert doc["schema"] == "ops_dynamical_l2_eval_v1"
