from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_lane_summary_v1(tmp_path: Path):
    src = tmp_path / "src.json"
    out = tmp_path / "out.json"

    src.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_report_v1",
                "top_global_singularities": [
                    {"row_id": "a", "lane": "canon", "best_regime": "bull_pump", "score": 0.9},
                    {"row_id": "b", "lane": "dss", "best_regime": "bear_trend", "score": 0.95},
                    {"row_id": "c", "lane": "canon", "best_regime": "bear_trend", "score": 0.8},
                    {"row_id": "d", "lane": "canon", "best_regime": "bull_pump", "score": 0.7},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_lane_summary_v1.py",
        "--input-json",
        str(src),
        "--top-n",
        "2",
        "--output-json",
        str(out),
    ]
    subprocess.run(cmd, check=True, cwd=Path(__file__).resolve().parents[1])

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_lane_summary_v1"
    assert data["counts"]["canon_rows_in_source_top"] == 3
    assert data["top_canon_global"][0]["row_id"] == "a"
    assert data["top_canon_by_regime"]["bull_pump"][0]["row_id"] == "a"
    assert data["top_canon_by_regime"]["bear_trend"][0]["row_id"] == "c"

