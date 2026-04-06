# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test for eval_prophecy_hit_rate_v1.py JSON output shape.
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "eval_prophecy_hit_rate_v1.py"


def test_eval_prophecy_hit_rate_price_mode_json(tmp_path: Path) -> None:
    score = tmp_path / "score.json"
    score.write_text(
        json.dumps({"predicted_direction": "bear", "actual_direction": "bear"}),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [sys.executable, str(_SCRIPT), "--run-mode", "price", "--score-json", str(score), "--stdout-only"],
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(cp.stdout)
    assert doc.get("schema") == "prophecy_hit_rate_eval_report_v2"
    assert doc.get("run_mode") == "price"
    assert doc.get("metrics", {}).get("n_evaluated") == 1
    assert doc.get("metrics", {}).get("price_directional_hit_rate") == 1.0


def test_eval_prophecy_script_exists() -> None:
    assert _SCRIPT.is_file(), str(_SCRIPT)
