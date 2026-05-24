"""Smoke: sweep_prophecy_headline_deadzone_hold_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sweep_prophecy_headline_deadzone_hold_v1.py"


def test_sweep_headline_deadzone_hold_smoke(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    per_date = tmp_path / "per_date.json"
    score.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "instrument": "btc",
                        "eval_date": "2025-01-02",
                        "predicted_direction": "bull",
                        "actual_direction": "bull",
                    },
                    {
                        "instrument": "btc",
                        "eval_date": "2025-01-03",
                        "predicted_direction": "bear",
                        "actual_direction": "bull",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    per_date.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "eval_date": "2025-01-02",
                        "instrument": "btc",
                        "confidence": 0.30,
                        "weighted_score": 0.25,
                    },
                    {
                        "eval_date": "2025-01-03",
                        "instrument": "btc",
                        "confidence": 0.10,
                        "weighted_score": -0.05,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "sweep.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--score-json",
            str(score),
            "--per-date-json",
            str(per_date),
            "--min-confidence-grid",
            "0.0,0.2",
            "--score-abs-deadzone-grid",
            "0.0,0.2",
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
    assert doc.get("schema") == "prophecy_headline_deadzone_hold_sweep_v1"
    assert doc.get("research_only") is True
    assert float(doc["baseline_all"]["price_directional_hit_rate_all"]) == 0.5
    assert doc.get("top_candidates")
