# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 88
# Purpose: Contract smoke tests for survivor crash correlation backtest draft script.
# Keywords: pytest, btrack, survivor, correlation, crash
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_btrack_survivor_crash_correlation_backtest_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_survivor_backtest_draft_generates_output_with_inferred_survivors(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    resonance = tmp_path / "resonance.jsonl"
    kospi = tmp_path / "kospi.csv"
    btc = tmp_path / "btc.csv"
    output = tmp_path / "out.json"

    _write_json(
        knowledge,
        {
            "schema": "bible_meaning_knowledge_ip_report_v1",
            "summary": {"candidate_count": 6, "survivor_count": 2},
        },
    )
    _write_json(
        candidates,
        {
            "schema": "bible_meaning_insight_candidates_v1",
            "candidates": [
                {"candidate_id": "cand_001", "hub_score": 0.9, "path_score": 0.5, "cluster_size": 9},
                {"candidate_id": "cand_002", "hub_score": 0.8, "path_score": 0.5, "cluster_size": 8},
                {"candidate_id": "cand_003", "hub_score": 0.1, "path_score": 0.1, "cluster_size": 1},
            ],
        },
    )
    _write_text(
        resonance,
        "\n".join(
            [
                json.dumps({"date": "2020-01-01", "candidate_id": "cand_001", "resonance_score": 1.0}),
                json.dumps({"date": "2020-01-01", "candidate_id": "cand_002", "resonance_score": 0.5}),
                json.dumps({"date": "2020-01-02", "candidate_id": "cand_001", "resonance_score": 0.2}),
                json.dumps({"date": "2020-01-02", "candidate_id": "cand_002", "resonance_score": 0.1}),
                "",
            ]
        ),
    )
    _write_text(
        kospi,
        "Date,Close\n2020-01-01,100\n2020-01-02,99\n2020-01-03,95\n",
    )
    _write_text(
        btc,
        "Date,Close\n2020-01-01,1000\n2020-01-02,1005\n2020-01-03,990\n",
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
            "--output",
            str(output),
            "--max-lag-days",
            "1",
            "--permutation-rounds",
            "10",
            "--seed",
            "7",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    out = json.loads(output.read_text(encoding="utf-8-sig"))
    assert out.get("schema") == "btrack_survivor_crash_correlation_backtest_v1"
    assert len(out.get("survivors") or []) == 2
    assert (out.get("analysis") or {}).get("kospi") is not None
    assert (out.get("analysis") or {}).get("btc") is not None
    warnings = out.get("warnings") or []
    assert "survivors_inferred_from_candidate_ranking" in warnings

