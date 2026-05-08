from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_mkm_myeongni_response_v2.py"
VALIDATE = ROOT / "scripts" / "validate_mkm_myeongni_response_v2.py"


def test_build_mkm_myeongni_response_v2_smoke(tmp_path: Path):
    lens = tmp_path / "lens.json"
    weather = tmp_path / "weather.json"
    out = tmp_path / "out.json"

    lens.write_text(
        json.dumps(
            {
                "scores": {"direction_score": -0.4, "confidence": 0.58},
                "advanced": {
                    "coordinator": {
                        "mkm_myeongni_math": {
                            "status": "ok",
                            "arbitrated_direction_score": -0.45,
                            "arbitrated_confidence": 0.6,
                            "ten_god_balance": -0.2,
                            "jijangan_pressure": 0.31,
                            "school_disagreement_index": 0.22,
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
        json.dumps(
            {
                "summary": {
                    "direct_match_rate": 0.7,
                    "reproducible_evidence_rate": 0.95,
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--lens-json",
            str(lens),
            "--weather-quality-json",
            str(weather),
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


def test_build_mkm_myeongni_response_v2_attack_profile_with_coverage_fallback(tmp_path: Path):
    lens = tmp_path / "lens.json"
    weather = tmp_path / "weather.json"
    out = tmp_path / "out_attack.json"

    lens.write_text(
        json.dumps(
            {
                "scores": {"direction_score": 0.36, "confidence": 0.61},
                "advanced": {"coordinator": {"mkm_myeongni_math": {"status": "ok"}}},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    weather.write_text(
        json.dumps(
            {"summary": {"coverage_rate": 0.8, "reproducible_evidence_rate": 0.9}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    cp = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--lens-json",
            str(lens),
            "--weather-quality-json",
            str(weather),
            "--profile",
            "attack",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout

    out_doc = json.loads(out.read_text(encoding="utf-8"))
    assert out_doc["calibration"]["profile"] == "attack"
    assert out_doc["coordinator_layer"]["failed_check_keys"] == []
