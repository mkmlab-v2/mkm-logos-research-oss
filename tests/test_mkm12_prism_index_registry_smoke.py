# -*- coding: utf-8 -*-
"""MKM12 Prism registry JSON: schema smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "docs" / "final" / "MKM12_PRISM_INDEX_REGISTRY_V1.json"


def test_prism_registry_loads_and_shape() -> None:
    assert REG.is_file(), f"missing {REG}"
    doc = json.loads(REG.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm12_prism_index_registry_v1"
    assert isinstance(doc.get("entries"), list) and len(doc["entries"]) >= 1
    for e in doc["entries"]:
        assert e.get("id")
        assert e.get("prism_axis") in ("S", "L", "K", "M")
        assert e.get("physical_path")
        assert e.get("agent_access")
