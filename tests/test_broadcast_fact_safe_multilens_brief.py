from scripts.broadcast_fact_safe_multilens_brief import _extract


def test_extract_key_value_from_markdown_line():
    md = "- reliability_badge: HIGH\n- gate_reason: monthly_check_gate\n"
    assert _extract(md, "reliability_badge") == "HIGH"
    assert _extract(md, "gate_reason") == "monthly_check_gate"


def test_extract_returns_none_when_missing():
    md = "- other: value\n"
    assert _extract(md, "history net_delta") is None
