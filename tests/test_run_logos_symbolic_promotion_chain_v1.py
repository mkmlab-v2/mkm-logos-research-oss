from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_symbolic_promotion_chain_v1.py"
NEWS_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_news_smoke_v1.jsonl"
LABEL_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_labels_smoke_v1.jsonl"
MAP_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_map_smoke_v1.json"


def test_run_logos_symbolic_promotion_chain_smoke(tmp_path: Path):
    bt_json = tmp_path / "bt.json"
    bt_csv = tmp_path / "bt.csv"
    gate_json = tmp_path / "gate.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
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
            "--backtest-json",
            str(bt_json),
            "--backtest-csv",
            str(bt_csv),
            "--gate-json",
            str(gate_json),
            "--min-samples",
            "3",
            "--min-hit-rate",
            "0.5",
            "--min-symbol-coverage",
            "3",
            "--min-non-synthetic-samples",
            "1",
            "--allow-fixture-fallback",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    out = json.loads(cp.stdout.strip())
    assert out.get("schema") == "logos_symbolic_promotion_chain_v1"
    assert out.get("all_pass") is True
    assert out.get("decision") == "GO_RESEARCH_PROMOTION_CANDIDATE"
    assert bt_json.is_file()
    assert bt_csv.is_file()
    assert gate_json.is_file()
    gate_doc = json.loads(gate_json.read_text(encoding="utf-8"))
    refs = gate_doc.get("input_refs") or {}
    assert refs.get("news_jsonl")
    assert refs.get("labels_jsonl")

