from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_compression_bridge_size_promotion_gate_smoke(tmp_path: Path) -> None:
    holdout = tmp_path / "holdout.json"
    walkforward = tmp_path / "walkforward.json"
    gate = tmp_path / "gate.json"
    holdout.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "status": "ok",
                        "prediction_direction_on": "bull",
                        "prediction_direction_off": "bull",
                        "delta_price_directional_hit_rate": 0.0,
                        "delta_size_weighted_payoff_mean": 0.00001,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    walkforward.write_text(
        json.dumps(
            {
                "decision": "PASS_WALKFORWARD_SIZE_LANE",
                "summary": {
                    "direction_changed_rows": 0,
                    "min_delta_price_directional_hit_rate": 0.0,
                    "min_delta_size_weighted_payoff_mean": 0.00001,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "check_compression_bridge_size_promotion_gate_v1.py"),
            "--holdout-eval",
            str(holdout),
            "--walkforward-eval",
            str(walkforward),
            "--output",
            str(gate),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(gate.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_bridge_size_promotion_gate_v1"
    assert doc.get("decision") == "GO_SIZE_LANE_PROMOTION_CONFIRMED"

