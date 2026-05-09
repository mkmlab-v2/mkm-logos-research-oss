from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "calibrate_mkm_myeongni_response_v2_thresholds_v1.py"


def test_calibrate_mkm_myeongni_response_v2_thresholds_smoke(tmp_path: Path):
    lens = tmp_path / "lens.json"
    weather = tmp_path / "weather.json"
    out = tmp_path / "calib.json"

    lens.write_text(
        json.dumps(
            {
                "scores": {"direction_score": -0.4, "confidence": 0.62},
                "advanced": {
                    "coordinator": {
                        "mkm_myeongni_math": {
                            "status": "ok",
                            "arbitrated_direction_score": -0.45,
                            "arbitrated_confidence": 0.64,
                            "ten_god_balance": -0.2,
                            "jijangan_pressure": 0.3,
                            "school_disagreement_index": 0.2,
                        }
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    weather.write_text(
        json.dumps({"summary": {"direct_match_rate": 0.75, "reproducible_evidence_rate": 0.95}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--lens-json", str(lens), "--weather-quality-json", str(weather), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_myeongni_response_v2_calibration_v1"
    rec = doc["recommended"]
    assert 0.36 <= rec["hold_confidence_cut"] <= 0.46
