"""Smoke: eval_prophecy_headline_confidence_holdout_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_prophecy_headline_confidence_holdout_v1.py"


def test_holdout_smoke(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    per_date = tmp_path / "per_date.json"
    rows_score = []
    rows_pd = []
    for i, d in enumerate(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"]):
        for inst in ("btc", "kospi"):
            rows_score.append(
                {
                    "instrument": inst,
                    "eval_date": d,
                    "predicted_direction": "bull" if i % 2 == 0 else "bear",
                    "actual_direction": "bull",
                }
            )
        rows_pd.append(
            {
                "eval_date": d,
                "instrument": "btc",
                "confidence": 0.25 if i < 2 else 0.10,
                "weighted_score": 0.2,
            }
        )
    score.write_text(json.dumps({"rows": rows_score}), encoding="utf-8")
    per_date.write_text(json.dumps({"rows": rows_pd}), encoding="utf-8")
    out = tmp_path / "holdout.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--score-json",
            str(score),
            "--per-date-json",
            str(per_date),
            "--train-fraction",
            "0.5",
            "--min-test-hit-rate",
            "0.0",
            "--min-coverage-active",
            "0.0",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_headline_confidence_holdout_v1"
    assert doc.get("test", {}).get("holdout_pass") is True
