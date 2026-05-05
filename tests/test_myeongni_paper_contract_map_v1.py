# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MAP = _ROOT / "data" / "myeongni" / "paper_contract_maps" / "yang_2015_four_pillars_personality_map_v1.json"


def test_yang_2015_map_loads_and_has_mappings():
    doc = json.loads(_MAP.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_paper_contract_map_v1"
    assert doc.get("paper", {}).get("doi") == "10.3349/ymj.2015.56.3.698"
    rows = doc.get("mkm_field_mappings") or []
    kinds = {r.get("mapping_kind") for r in rows}
    assert "gap" in kinds
    assert "partial_analogy" in kinds
