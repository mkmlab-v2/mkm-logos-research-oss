"""PersonaDiary Figma design sync — map vs Android tokens SSOT."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs/final/artifacts/personadiary_figma_token_map_v1.json"
FIGMA_SSOT = ROOT / "docs/final/artifacts/personadiary_figma_design_ssot_v1_latest.json"
SYNC = ROOT / "scripts/sync_personadiary_figma_design_tokens_v1.py"
GATE = ROOT / "scripts/check_personadiary_figma_design_sync_gate_v1.py"


def test_personadiary_figma_map_and_sync_gate() -> None:
    map_doc = json.loads(MAP.read_text(encoding="utf-8"))
    figma_ssot = json.loads(FIGMA_SSOT.read_text(encoding="utf-8"))
    assert map_doc["schema"] == "personadiary_figma_token_map_v1"
    assert figma_ssot["schema"] == "personadiary_figma_design_ssot_v1"
    assert map_doc["figma_file_key"] == figma_ssot["figma_file_key"]
    assert len(map_doc.get("variables") or []) >= 16

    proc = subprocess.run([sys.executable, str(GATE)], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    from scripts.sync_personadiary_figma_design_tokens_v1 import validate_map_against_android
    from scripts.personadiary_android_design_tokens_v1 import load_ssot

    android = load_ssot()
    assert validate_map_against_android(map_doc, android) == []
