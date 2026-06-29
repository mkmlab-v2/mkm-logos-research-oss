"""PersonaDiary Android design tokens v1 — schema + CSS gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SSOT = ROOT / "docs/final/artifacts/personadiary_android_design_tokens_v1_latest.json"
SCHEMA = ROOT / "docs/final/schemas/personadiary_android_design_tokens_v1.schema.json"
CSS = ROOT / "projects/no1kmedi/src/app/globals.css"
GATE = ROOT / "scripts/check_personadiary_android_design_tokens_gate_v1.py"


def test_personadiary_android_design_tokens_schema_and_css_gate() -> None:
    doc = json.loads(SSOT.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)

    from scripts.personadiary_android_design_tokens_v1 import validate_ssot

    assert validate_ssot(doc, css_path=CSS) == []

    proc = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_css_drift_detected_for_palette() -> None:
    from scripts.personadiary_android_design_tokens_v1 import load_ssot, validate_css_alignment

    doc = load_ssot(SSOT)
    broken = doc.copy()
    broken["palette"] = dict(doc["palette"])
    broken["palette"]["tint"] = "#ff00ff"
    css_text = CSS.read_text(encoding="utf-8")
    errors = validate_css_alignment(broken, css_text)
    assert any("palette_hex_missing:tint" in e for e in errors)
