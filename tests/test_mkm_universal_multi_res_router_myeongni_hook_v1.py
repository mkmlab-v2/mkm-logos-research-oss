# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
MDC = _ROOT / ".cursor/rules/mkm-universal-multi-res-router-myeongni-v1.mdc"


def test_myeongni_u2c_hook_mdc_exists():
    assert MDC.is_file(), f"missing U2c hook: {MDC}"
    text = MDC.read_text(encoding="utf-8")
    assert "alwaysApply: false" in text
    assert "universal_multi_res_router_v1.py" in text
    assert "myeongni_expectation_vs_fact_matrix_v1_lite.md" in text
    assert "myeongni_conflict_arbitration_runtime_mode_latest.json" in text
