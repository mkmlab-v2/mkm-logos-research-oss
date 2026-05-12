from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_EXPLAINABLE = ROOT / "scripts" / "build_general_prophecy_explainable_v1.py"
BUILD_QUALITY = ROOT / "scripts" / "report_general_prophecy_explainability_quality_v1.py"
BUILD_HOLDOUT = ROOT / "scripts" / "build_general_prophecy_explainability_holdout_report_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "general_prophecy_registry_sample_v1.json"


def _run(script: Path, args: list[str]) -> None:
    cp = subprocess.run([sys.executable, str(script), *args], cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout


def test_holdout_report_smoke(tmp_path: Path):
    explainable = tmp_path / "explainable.json"
    quality = tmp_path / "quality.json"
    holdout = tmp_path / "holdout.json"

    _run(BUILD_EXPLAINABLE, ["--input", str(FIXTURE), "--output", str(explainable)])
    _run(BUILD_QUALITY, ["--input", str(explainable), "--output", str(quality)])
    _run(BUILD_HOLDOUT, ["--input", str(quality), "--output", str(holdout)])

    doc = json.loads(holdout.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_explainability_holdout_report_v1"
    assert doc["overall"]["n_questions"] >= 1
    assert doc["overall"]["direct_match_rate"] is not None
    assert doc["overall"]["direct_match_rate"] > 0.0
    assert "holdout_core" in doc
    assert isinstance(doc.get("cohorts"), dict)
