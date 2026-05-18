# @MKM12-METADATA
# Type: Logic
# Purpose: Logos metaphor DB thin slice schema + render card builder.
# Keywords: logos, track_b, research_metaphor, NON_GATING

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA = _ROOT / "docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json"
_THEME = _ROOT / "docs/research/logos_metaphor_db_v1/theme_01_blood_and_water.json"
_RUNNER = _ROOT / "scripts/build_logos_research_card_v1.py"


def test_schema_and_theme_exist() -> None:
    assert _SCHEMA.is_file()
    assert _THEME.is_file()
    doc = json.loads(_THEME.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_logos_research_thin_slice_v0.2.1"
    assert doc["meta"]["gating_status"] == "NON_GATING"


def test_json_schema_valid_draft07() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.Draft7Validator(schema).validate(json.loads(_THEME.read_text(encoding="utf-8")))


def test_runner_validate_only() -> None:
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--theme-json", str(_THEME), "--validate-only"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    assert "OK" in cp.stdout


def test_render_contains_barrier_and_anchor() -> None:
    cp = subprocess.run(
        [sys.executable, str(_RUNNER), "--theme-json", str(_THEME)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    assert "NON_GATING" in cp.stdout
    assert "ANCHOR_JOHN_19_34" in cp.stdout
    assert "NODE_LEV_17_11" in cp.stdout
    assert "research_metaphor_" in cp.stdout
