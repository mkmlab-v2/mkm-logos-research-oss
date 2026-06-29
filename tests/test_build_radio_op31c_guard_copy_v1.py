"""radio_op31c_guard_copy_v1 builder smoke."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/artifacts/schemas/radio_op31c_guard_copy_v1.schema.json"


def test_build_radio_op31c_guard_copy_v1_schema():
    from scripts.build_radio_op31c_guard_copy_v1 import build_guard_copy

    doc = build_guard_copy()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    assert "jemaai.cloud" in doc["disclaimers"]["delayed_observability"]["ko"]
    assert doc["operational_posture"]["go_live_default"].startswith("hold")
    never = "\n".join(doc["never_publish"])
    assert "47.5" in never or "적중률" in never
    pinned = doc["studio_paste_blocks"]["pinned_comment_mkm"]["ko"]
    assert "투자" in pinned and "jemaai.cloud" in pinned
