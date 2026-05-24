"""radio_youtube_channel_copy_v1 builder smoke."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/artifacts/schemas/radio_youtube_channel_copy_v1.schema.json"


def test_build_radio_youtube_channel_copy_v1_schema():
    from scripts.build_radio_youtube_channel_copy_v1 import build_copy

    doc = build_copy()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)
    mkm = doc["channels"]["mkm_radio"]
    assert "MKM Field Radio" in mkm["display_name_primary"]
    assert "투자" in mkm["description_ko"]
    tkm = doc["channels"]["tkm_health_24h"]
    assert "비진료" in tkm["display_name_secondary"] or "비진료" in tkm["description_ko"]
    for ch in doc["channels"].values():
        name_blob = ch["display_name_primary"] + ch["display_name_secondary"]
        assert "57.3" not in name_blob
        assert "매수" not in name_blob
        assert "완치" not in name_blob

