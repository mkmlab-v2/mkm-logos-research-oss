"""Tests for wrong-direction lens diagnostic report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wrong_direction_lens_report_smoke(tmp_path: Path) -> None:
    miss = {
        "misses": [
            {
                "miss_kind": "wrong_direction",
                "eval_date": "2026-04-02",
                "predicted_direction": "bull",
                "actual_direction": "bear",
            }
        ]
    }
    per_date = {
        "rows": [
            {
                "eval_date": "2026-04-02",
                "instrument": "btc",
                "preliminary_direction": "bull",
                "weighted_score": 0.24,
                "confidence": 0.25,
                "lens_values": {
                    "price": {"score": 0.26, "confidence": 0.26},
                    "macro": {"score": 0.33, "confidence": 0.3},
                },
                "weights": {"price": 0.65, "macro": 0.2},
            }
        ]
    }
    miss_path = tmp_path / "miss.json"
    per_path = tmp_path / "per_date.json"
    out_path = tmp_path / "out.json"
    miss_path.write_text(json.dumps(miss), encoding="utf-8")
    per_path.write_text(json.dumps(per_date), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_btrack_wrong_direction_lens_report_v1.py",
            "--miss-report",
            str(miss_path),
            "--per-date-json",
            str(per_path),
            "--output",
            str(out_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["n_wrong_direction_days"] == 1
    day = doc["wrong_direction_days"][0]
    assert day["lens_values"]["price"]["implied_sign"] == "bull"
    assert "operator_line" in doc
