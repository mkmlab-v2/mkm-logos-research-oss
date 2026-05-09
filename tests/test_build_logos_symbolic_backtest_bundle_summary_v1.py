from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKTEST_SCRIPT = ROOT / "scripts" / "run_logos_symbolic_event_backtest_v1.py"
MAP_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_map_smoke_v1.json"
NEWS_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_news_smoke_v1.jsonl"
LABEL_FIX = ROOT / "tests" / "fixtures" / "logos_symbolic_event_backtest_labels_smoke_v1.jsonl"
BUNDLE_SCRIPT = ROOT / "scripts" / "build_logos_symbolic_backtest_bundle_summary_v1.py"


def _run_backtest(tmp_path: Path, out_json: Path) -> None:
    out_csv = tmp_path / (out_json.stem + ".csv")
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


def test_build_logos_symbolic_backtest_bundle_summary_dedup_smoke(tmp_path: Path):
    # Create two identical backtest JSONs; dedupe should collapse to the unique
    # observation_id|label_date set from a single run.
    out_json1 = tmp_path / "bt1.json"
    out_json2 = tmp_path / "bt2.json"
    _run_backtest(tmp_path, out_json1)
    _run_backtest(tmp_path, out_json2)

    out_bundle = tmp_path / "bundle.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(BUNDLE_SCRIPT),
            "--inputs",
            str(out_json1),
            str(out_json2),
            "--output-json",
            str(out_bundle),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    bundle = json.loads(out_bundle.read_text(encoding="utf-8"))
    assert bundle.get("schema") == "logos_symbolic_event_backtest_bundle_summary_v1"

    agg = bundle.get("aggregate") or {}
    assert agg.get("run_count") == 2
    assert agg.get("total_n_evaluated") == 8  # 4 rows per run (smoke fixture) * 2
    assert agg.get("weighted_hit_rate") == 1.0

    uniq = (agg.get("unique_by_observation_label") or {})
    assert uniq.get("n_evaluated") == 4
    assert uniq.get("hit_rate") == 1.0
    assert uniq.get("non_synthetic_n") == 4
    assert uniq.get("non_synthetic_hit_rate") == 1.0

