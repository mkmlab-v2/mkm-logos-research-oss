"""Gemini concept bridge builder (dry-run path)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_logos_concept_bridge_gemini_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_concept_bridge_v1.schema.json"


def test_gemini_bridge_dry_run_schema(tmp_path: Path) -> None:
    out = tmp_path / "bridge.json"
    cp = subprocess.run(
        [sys.executable, str(BUILDER), "--dry-run", "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["policy"]["llm_api_called"] is False
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
