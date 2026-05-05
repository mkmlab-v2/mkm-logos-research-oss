from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKTEST_SCRIPT = ROOT / "scripts" / "run_logos_symbolic_event_backtest_v1.py"
GATE_SCRIPT = ROOT / "scripts" / "check_logos_symbolic_event_promotion_gate_v1.py"
NEWS_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_news_smoke_v1.jsonl"
LABEL_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_labels_smoke_v1.jsonl"
MAP_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_map_smoke_v1.json"


def test_logos_symbolic_event_backtest_smoke(tmp_path: Path):
    out_json = tmp_path / "bt.json"
    out_csv = tmp_path / "bt.csv"
    cp = subprocess.run(
        [
            sys.executable,
            str(BACKTEST_SCRIPT),
            "--news-jsonl",
            str(NEWS_FIX),
            "--labels-jsonl",
            str(LABEL_FIX),
            "--symbol-map-json",
            str(MAP_FIX),
            "--instrument-id",
            "KOSPI",
            "--horizon",
            "1d",
            "--neutral-score-band",
            "0.2",
            "--output-json",
            str(out_json),
            "--output-csv",
            str(out_csv),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_symbolic_event_backtest_v1"
    assert doc.get("summary", {}).get("n_evaluated") == 4
    assert doc.get("summary", {}).get("hit_rate") == 1.0
    assert doc.get("summary", {}).get("symbol_coverage_count") >= 4
    assert doc.get("summary", {}).get("non_synthetic_n_evaluated") == 4
    split_summary = doc.get("split_summary") or {}
    assert "train_holdout" in split_summary
    assert split_summary["train_holdout"]["n_evaluated"] == 4
    assert out_csv.is_file()


def test_logos_symbolic_event_promotion_gate_smoke(tmp_path: Path):
    backtest_json = tmp_path / "bt.json"
    backtest_json.write_text(
        json.dumps(
            {
                "schema": "logos_symbolic_event_backtest_v1",
                "summary": {
                    "n_evaluated": 50,
                    "hit_rate": 0.61,
                    "symbol_coverage_count": 4,
                    "non_synthetic_n_evaluated": 25,
                },
                "split_summary": {
                    "locked_eval": {
                        "n_evaluated": 10,
                        "hits": 6,
                        "hit_rate": 0.6,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    out_gate = tmp_path / "gate.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--backtest-json",
            str(backtest_json),
            "--out",
            str(out_gate),
            "--min-samples",
            "30",
            "--min-hit-rate",
            "0.55",
            "--min-symbol-coverage",
            "3",
            "--min-holdout-samples",
            "8",
            "--min-holdout-hit-rate",
            "0.55",
            "--min-non-synthetic-samples",
            "20",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    gate = json.loads(out_gate.read_text(encoding="utf-8"))
    assert gate.get("schema") == "logos_symbolic_event_promotion_gate_v1"
    assert gate.get("all_pass") is True
    assert gate.get("decision") == "GO_RESEARCH_PROMOTION_CANDIDATE"
    assert gate.get("track_wall", {}).get("promotion_to_a_track_allowed") is False

