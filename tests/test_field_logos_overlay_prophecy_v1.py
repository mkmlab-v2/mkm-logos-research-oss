"""Field×Logos overlay prophecy lane smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_field_logos_overlay_prophecy_v1.py"
EVAL = ROOT / "scripts/eval_field_logos_overlay_prophecy_v1.py"
SCHEMA = ROOT / "docs/final/schemas/field_logos_overlay_prophecy_v1.schema.json"
FIELD_SNAPSHOT = ROOT / "reports/field_regime_observational_snapshot_v1_latest.json"
LOGOS_RESONANCE = ROOT / "docs/final/artifacts/logos_regime_resonance_shadow_signal_latest.json"
HOLDOUT = ROOT / "docs/final/fixtures/field_logos_overlay_prophecy_holdout_v1.json"


def test_build_and_eval_field_logos_overlay_prophecy(tmp_path: Path) -> None:
    overlay_out = tmp_path / "overlay.json"
    eval_out = tmp_path / "eval.json"

    cp = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--field-snapshot-json",
            str(FIELD_SNAPSHOT),
            "--logos-resonance-json",
            str(LOGOS_RESONANCE),
            "--holdout-json",
            str(HOLDOUT),
            "--output-json",
            str(overlay_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr

    doc = json.loads(overlay_out.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert doc["track_wall"]["field_primary_logos_secondary"] is True
    assert len(doc["predictions"]) >= 2

    blood = next(p for p in doc["predictions"] if p["prediction_id"] == "h01_blood_water")
    bridges = blood["logos_axis"]["bridge_artifacts"]
    assert any("q13_passion_blood_water" in b for b in bridges)
    assert any("John.19.34" in v for v in blood["logos_axis"]["verse_ids"])

    cp2 = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--overlay-json",
            str(overlay_out),
            "--holdout-json",
            str(HOLDOUT),
            "--output-json",
            str(eval_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp2.returncode == 0, cp2.stderr
    ev = json.loads(eval_out.read_text(encoding="utf-8"))
    assert ev["summary"]["pass_rate"] >= 0.5
    blood_row = next(r for r in ev["rows"] if r.get("holdout_id") == "h01_blood_water")
    assert blood_row["passed"] is True
