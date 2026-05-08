from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY_SET = ROOT / "docs" / "final" / "artifacts" / "logos_semantic_query_set_weekly_v1.json"


def test_logos_semantic_query_set_weekly_v1_shape() -> None:
    doc = json.loads(QUERY_SET.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_semantic_query_set_v1"
    queries = doc.get("queries")
    assert isinstance(queries, list)
    assert 20 <= len(queries) <= 30
    assert len(set(queries)) == len(queries)
    assert all(isinstance(q, str) and q.strip() for q in queries)
