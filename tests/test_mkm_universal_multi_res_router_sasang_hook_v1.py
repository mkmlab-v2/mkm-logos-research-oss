# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
MDC = _ROOT / ".cursor/rules/mkm-universal-multi-res-router-sasang-v1.mdc"


def test_sasang_u2_hook_mdc_exists():
    assert MDC.is_file(), f"missing U2 hook: {MDC}"
    text = MDC.read_text(encoding="utf-8")
    assert "alwaysApply: false" in text
    assert "universal_multi_res_router_v1.py" in text
    assert "sasang_expectation_vs_fact_matrix_v1.md" in text
    assert "hold_gate" in text
    assert "vector_4d" in text
