# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 88
# Purpose: Smoke test for L0 early-warning survivor resonance backtest.
# Keywords: pytest, btrack, survivor, l0, early-warning
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_btrack_survivor_l0_early_warning_backtest_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_l0_early_warning_backtest_generates_expected_contract(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    resonance = tmp_path / "resonance.jsonl"
    kospi = tmp_path / "kospi.csv"
    btc = tmp_path / "btc.csv"
    out = tmp_path / "out.json"

    _write_json(knowledge, {"summary": {"survivor_count": 2}, "survivor_ids": ["cand_001", "cand_002"]})
    _write_json(
        candidates,
        {
            "candidates": [
                {"candidate_id": "cand_001", "hub_score": 0.9},
                {"candidate_id": "cand_002", "hub_score": 0.8},
            ]
        },
    )
    _write_text(
        resonance,
        "\n".join(
            [
                json.dumps({"date": "2020-01-01", "candidate_id": "cand_001", "resonance_score": 0.8}),
                json.dumps({"date": "2020-01-02", "candidate_id": "cand_001", "resonance_score": 0.9}),
                json.dumps({"date": "2020-01-03", "candidate_id": "cand_002", "resonance_score": 0.7}),
                json.dumps({"date": "2020-01-04", "candidate_id": "cand_002", "resonance_score": 0.6}),
                json.dumps({"date": "2020-01-05", "candidate_id": "cand_001", "resonance_score": 0.95}),
            ]
        ),
    )
    _write_text(
        kospi,
        "Date,Close\n2020-01-01,100\n2020-01-02,101\n2020-01-03,85\n2020-01-04,84\n2020-01-05,83\n",
    )
    _write_text(
        btc,
        "Date,Close\n2020-01-01,1000\n2020-01-02,995\n2020-01-03,996\n2020-01-04,800\n2020-01-05,790\n",
    )

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--resonance-jsonl",
            str(resonance),
            "--kospi-csv",
            str(kospi),
            "--btc-csv",
            str(btc),
            "--crash-dd-threshold",
            "-0.10",
            "--onset-horizon-days",
            "2",
            "--max-lag-days",
            "1",
            "--permutation-rounds",
            "10",
            "--seed",
            "7",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "btrack_survivor_l0_early_warning_backtest_v1"
    assert doc["l0_warning_only"] is True
    assert (doc["analysis"]["kospi"]["lags"]) and (doc["analysis"]["btc"]["lags"])
    assert "onset_horizon_days" in doc["inputs"]
