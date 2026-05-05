from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_mkm_logos_response_v2.py"
VALIDATE = ROOT / "scripts" / "validate_mkm_logos_response_v2.py"


def test_build_mkm_logos_response_v2_smoke(tmp_path: Path):
    fractal = tmp_path / "fractal.json"
    compare = tmp_path / "compare.json"
    monitor = tmp_path / "monitor.json"
    weekly = tmp_path / "weekly.json"
    out = tmp_path / "out.json"

    fractal.write_text(
        json.dumps(
            {
                "top_match": {"archetype_id": "kingdom", "resonance_cosine": 0.9},
                "current_vector_slkm": {"S": 0.5, "L": 0.5, "K": 0.6, "M": 0.55},
                "decision": {"signal": "WATCH"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    compare.write_text(json.dumps({"delta_mixed_minus_pure": -0.08}) + "\n", encoding="utf-8")
    monitor.write_text(json.dumps({"status": "PASS_LOW_BACKFILL_DEPENDENCE"}) + "\n", encoding="utf-8")
    weekly.write_text(json.dumps({"is_alert": False}) + "\n", encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--fractal-json",
            str(fractal),
            "--compare-json",
            str(compare),
            "--monitor-json",
            str(monitor),
            "--weekly-alert-json",
            str(weekly),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    cp2 = subprocess.run(
        [sys.executable, str(VALIDATE), "--response-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 0, cp2.stderr + cp2.stdout
    out_doc = json.loads(out.read_text(encoding="utf-8"))
    assert out_doc["coordinator_layer"]["direction_override_allowed"] is False
    assert out_doc["governance"]["action_policy_mode"] == "WATCH_FIRST"
    assert out_doc["response_layer"]["template_key"]
    assert isinstance(out_doc["evidence_links"], list) and out_doc["evidence_links"]

