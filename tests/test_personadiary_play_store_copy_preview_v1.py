"""Play Store copy preview v1 — PUBLIC_FACING aligned schema smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_play_store_copy_preview_v1.schema.json"
BUILDER = ROOT / "scripts/build_personadiary_play_store_copy_preview_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/personadiary_play_store_copy_preview_v1_latest.json"
FORBIDDEN = ("운세 확정", "47%", "매수 사인")


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_build_play_store_copy_preview_exit0(schema: dict) -> None:
    proc = subprocess.run(
        [sys.executable, str(BUILDER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    blob = json.dumps(doc, ensure_ascii=False)
    for bad in FORBIDDEN:
        assert bad not in blob
    assert doc["preview_only"] is True
    assert doc["send_gate_default"] == "HOLD"
