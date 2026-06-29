"""Optional hygiene_prefs_hypo_v1 on personadiary_mobile_ops_v1."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_mobile_ops_v1.schema.json"
EXAMPLE_PATH = ROOT / "docs/final/artifacts/fixtures/personadiary_mobile_ops_v1.example.json"


def test_mobile_ops_accepts_hygiene_prefs_hypo_v1() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    doc = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    doc["hygiene_prefs_hypo_v1"] = {
        "hypothesis_tier": "B",
        "boundary_ack": "research_only · local queue tidy · no push · no OS block",
        "pull_window_local": "21:00",
        "native_shell_target": "web_pwa",
    }
    jsonschema.validate(instance=doc, schema=schema)
