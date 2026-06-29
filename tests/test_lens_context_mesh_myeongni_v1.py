"""Myeongni timeline lens context mesh pack smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_lens_context_mesh_myeongni_timeline_pack_v1.py"
HUB = ROOT / "docs/final/artifacts/lens_context_mesh_hub_myeongni_v1_latest.json"
HOP = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_myeongni_v1_latest.json"


def _schema(name: str) -> dict:
    return json.loads((ROOT / "docs/final/schemas" / name).read_text(encoding="utf-8-sig"))


def test_build_myeongni_timeline_pack_exit_zero() -> None:
    proc = subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=False)
    assert proc.returncode == 0
    assert HUB.is_file()
    assert HOP.is_file()


def test_myeongni_hub_schema() -> None:
    if not HUB.is_file():
        subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True)
    hub = json.loads(HUB.read_text(encoding="utf-8-sig"))
    jsonschema.validate(hub, _schema("lens_context_mesh_hub_v1.schema.json"))
    assert hub["lens_id"] == "myeongni"
    assert hub["ui_contract"]["visual_metaphor"] == "timeline_not_verse_graph"
    bridge = hub.get("manseryeok_bridge_v1") or {}
    assert bridge.get("schema") == "lens_context_mesh_manseryeok_bridge_v1"
    assert bridge.get("engine_linked") is True
