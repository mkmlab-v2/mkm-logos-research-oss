# Keywords: build_showroom_logos_research_slice_v1, logos, NON_GATING

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/build_showroom_logos_research_slice_v1.py"
SCHEMA = ROOT / "docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json"
DB_DIR = ROOT / "docs/research/logos_metaphor_db_v1"


def test_paths_exist() -> None:
    assert RUNNER.is_file()
    assert SCHEMA.is_file()
    assert list(DB_DIR.glob("theme_*.json"))


def test_build_slice_default_out(tmp_path: Path) -> None:
    out = tmp_path / "slice.json"
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "showroom_logos_research_slice_v0"
    assert doc["theme_count"] >= 7
    assert doc["disclaimer"]["gating_status"] == "NON_GATING"
    assert doc["disclaimer"]["evidence_tier"] == "hypo_research_only"
    themes = doc["themes"]
    assert themes[0]["golden_anchor"]["ref"]
    assert themes[0]["semantic_nodes"]


def test_build_slice_json_schema_themes(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    out = tmp_path / "slice2.json"
    subprocess.run(
        [sys.executable, str(RUNNER), "--out-json", str(out)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    for theme in doc["themes"]:
        theme_doc = {
            "schema": theme["schema"],
            "meta": theme["meta"],
            "golden_anchor": theme["golden_anchor"],
            "semantic_nodes": theme["semantic_nodes"],
            "governance_mapping": theme["governance_mapping"],
            "commander_insight": theme["commander_insight"],
        }
        validator.validate(theme_doc)
