"""Tests for herbs_formulas markdown → extract JSON builder (B-track)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_herbs_formulas_extract_v1.py"
INPUT_MD = ROOT / "tests/fixtures/herbs_formulas_lecture_extract_input_v1.md"
SCHEMA_PATH = ROOT / "docs/final/schemas/herbs_formulas_extract_v1.schema.json"

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def test_build_extract_from_fixture_md_has_required_clinical_fields() -> None:
    from scripts.build_herbs_formulas_extract_v1 import build_herbs_formulas_extract

    doc = build_herbs_formulas_extract(source_path=INPUT_MD)
    clinical = doc["payload"]["clinical"]
    assert clinical["primary_pathology"] == "表虚证"
    assert "恶风" in clinical["representative_symptoms"]
    assert doc["research_only"] is True
    assert doc["send_gate"] == "HOLD"
    assert doc["provenance"]["source_material_ids"] == [
        "fixture:lecture_bangje_2026_section4_demo"
    ]


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_extract_fixture_validates_against_schema() -> None:
    from scripts.build_herbs_formulas_extract_v1 import build_herbs_formulas_extract, validate_extract

    doc = build_herbs_formulas_extract(source_path=INPUT_MD)
    validate_extract(doc)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_cli_strict_exit_0(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(INPUT_MD), "--out", str(out), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "herbs_formulas_extract_v1"
    assert doc["payload"]["education"]["learning_objectives"]


def test_cli_missing_input_exit_2() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(ROOT / "missing_herbs_input.md")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
