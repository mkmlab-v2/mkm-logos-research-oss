from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY_SET = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"


def test_v4_ko_en_query_set_shape() -> None:
    doc = json.loads(QUERY_SET.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_semantic_query_set_v4_ko_en_v1"
    items = doc["items"]
    assert len(items) == 12
    for it in items:
        assert it.get("query_en") and it.get("query_ko")
