from __future__ import annotations

import json
from pathlib import Path

from scripts import build_worldview_formula_crosslink_bridge_v1 as bridge_mod


def test_worldview_formula_crosslink_bridge_ok() -> None:
    assert bridge_mod.main() == 0
    doc = json.loads(bridge_mod.OUT.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    assert doc["promotion_to_a_track_allowed"] is False
    names = {c["name"] for c in doc["checks"]}
    assert "formula_json_links_worldview" in names
    assert "worldview_links_formula_json" in names
