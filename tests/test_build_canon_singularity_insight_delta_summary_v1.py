from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_insight_delta_summary_v1(tmp_path: Path):
    hist = tmp_path / "hist.jsonl"
    out = tmp_path / "delta.json"
    e1 = {
        "schema": "original_corpus_regime_singularity_canon_insight_minimum_event_v1",
        "generated_at_utc": "2026-04-23T00:00:00Z",
        "insights": [
            {"row_id": "Gen.1.1", "best_regime": "bull_pump", "score": 0.4, "margin_vs_second": 0.1},
            {"row_id": "Gen.1.2", "best_regime": "bear_trend", "score": 0.3, "margin_vs_second": 0.1},
        ],
    }
    e2 = {
        "schema": "original_corpus_regime_singularity_canon_insight_minimum_event_v1",
        "generated_at_utc": "2026-04-24T00:00:00Z",
        "insights": [
            {"row_id": "Gen.1.1", "best_regime": "bull_pump", "score": 0.45, "margin_vs_second": 0.1},
            {"row_id": "Gen.1.3", "best_regime": "bear_trend", "score": 0.31, "margin_vs_second": 0.1},
        ],
    }
    hist.write_text(json.dumps(e1, ensure_ascii=False) + "\n" + json.dumps(e2, ensure_ascii=False) + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_insight_delta_summary_v1.py",
        "--history-jsonl",
        str(hist),
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_insight_delta_summary_v1"
    assert data["counts"]["added_count"] == 1
    assert data["counts"]["removed_count"] == 1
    assert data["counts"]["changed_count"] == 1

