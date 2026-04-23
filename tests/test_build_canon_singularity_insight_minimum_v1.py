from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_insight_minimum_v1(tmp_path: Path):
    src = tmp_path / "summary.json"
    out = tmp_path / "insight.json"
    src.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_lane_summary_v1",
                "top_canon_global": [
                    {
                        "row_id": "Gen.1.1",
                        "best_regime": "sideways_accumulation",
                        "score": 0.5,
                        "margin_vs_second": 0.1,
                        "state16": 2,
                        "text_preview": "abc",
                    },
                    {
                        "row_id": "Gen.1.2",
                        "best_regime": "sideways_accumulation",
                        "score": 0.5,
                        "margin_vs_second": 0.2,
                        "state16": 2,
                        "text_preview": "abc def",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_insight_minimum_v1.py",
        "--summary-json",
        str(src),
        "--top-n",
        "1",
        "--output-json",
        str(out),
        "--history-jsonl",
        str(tmp_path / "hist.jsonl"),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_insight_minimum_v1"
    assert data["counts"]["insight_rows"] == 1
    assert data["insights"][0]["row_id"] == "Gen.1.2"
    assert data["meta"]["rank_policy_version"] == "score_margin_tokendiv_v2"
    assert "token_diversity" in data["insights"][0]
    assert len(data["insights"][0]["commentary"]) > 20
    hist = (tmp_path / "hist.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(hist) == 1

