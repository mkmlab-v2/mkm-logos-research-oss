"""Contract tests for mergeInsightGraphBloomFromStatic (mirrors TS in magic-orb-graph-bloom.ts)."""


def _node_count(doc):
    if not doc:
        return 0
    nodes = (doc.get("graph_bloom") or {}).get("nodes")
    return len(nodes) if isinstance(nodes, list) else 0


def merge_insight_graph_bloom_from_static(primary, static_doc):
    """Python mirror of mergeInsightGraphBloomFromStatic — keep in sync with TS."""
    if not static_doc or not static_doc.get("graph_bloom"):
        return primary
    primary_n = _node_count(primary)
    static_n = _node_count(static_doc)
    if static_n <= primary_n or static_n < 8:
        return primary
    merged = {**primary, "graph_bloom": static_doc["graph_bloom"]}
    if static_doc.get("search_hud_v1"):
        merged["search_hud_v1"] = static_doc["search_hud_v1"]
    return merged


def _bloom(n):
    return {"graph_bloom": {"schema": "magic_orb_graph_bloom_v1", "nodes": [{}] * n, "edges": []}}


def test_kv_sparse_upgrades_from_static():
    primary = {**_bloom(18), "query_id": "q04", "rag_evidence": ["keep"]}
    static = {**_bloom(64), "search_hud_v1": {"this_query": {"node_count": 64}}}
    out = merge_insight_graph_bloom_from_static(primary, static)
    assert _node_count(out) == 64
    assert out["rag_evidence"] == ["keep"]
    assert out["search_hud_v1"]["this_query"]["node_count"] == 64


def test_kv_richer_keeps_primary():
    primary = _bloom(64)
    static = _bloom(18)
    out = merge_insight_graph_bloom_from_static(primary, static)
    assert _node_count(out) == 64


def test_no_static_bloom_unchanged():
    primary = _bloom(18)
    out = merge_insight_graph_bloom_from_static(primary, None)
    assert _node_count(out) == 18


def test_legacy_sparse_kv_below_12_still_upgrades():
    primary = _bloom(3)
    static = _bloom(64)
    out = merge_insight_graph_bloom_from_static(primary, static)
    assert _node_count(out) == 64
