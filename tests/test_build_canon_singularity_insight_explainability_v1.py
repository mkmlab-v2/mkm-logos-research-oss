from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_insight_explainability_v1(tmp_path: Path):
    src = tmp_path / "insight.json"
    out = tmp_path / "explain.json"
    src.write_text(
        json.dumps(
            {
                "schema": "original_corpus_regime_singularity_canon_insight_minimum_v1",
                "insights": [
                    {
                        "row_id": "Gen.1.1",
                        "best_regime": "sideways_accumulation",
                        "score": 0.5,
                        "margin_vs_second": 0.1,
                        "token_diversity": 0.4,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_insight_explainability_v1.py",
        "--insight-json",
        str(src),
        "--output-json",
        str(out),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_insight_explainability_v1"
    assert data["counts"]["rows"] == 1
    assert data["rows"][0]["top_driver"] in {
        "score_component",
        "margin_component",
        "token_diversity_component",
    }

