# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
MDC = _ROOT / ".cursor/rules/mkm-universal-multi-res-router-logos-v1.mdc"


def test_logos_u2b_hook_mdc_exists():
    assert MDC.is_file(), f"missing U2b hook: {MDC}"
    text = MDC.read_text(encoding="utf-8")
    assert "alwaysApply: false" in text
    assert "universal_multi_res_router_v1.py" in text
    assert "logos_expectation_vs_fact_matrix_v1_lite.md" in text
    assert "logos_context_inventory_v1_latest.json" in text
    assert "[NON_GATING]" in text
    assert "routing_hints_only" in text or "vector_4d" in text
