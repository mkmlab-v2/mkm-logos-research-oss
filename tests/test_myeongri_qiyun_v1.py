# -*- coding: utf-8 -*-
from __future__ import annotations

from scripts.myeongri_qiyun_v1 import compute_qiyun_meta_v1


def test_qiyun_positive_days_forward_and_backward():
    m_fwd = compute_qiyun_meta_v1(2000, 6, 15, 12, "경", True)
    assert m_fwd["forward"] is True
    assert m_fwd["qiyun_days"] > 0
    assert m_fwd["qiyun_years_float"] > 0

    m_bwd = compute_qiyun_meta_v1(2000, 6, 15, 12, "신", True)
    assert m_bwd["forward"] is False
    assert m_bwd["qiyun_days"] > 0


def test_qiyun_meta_schema():
    m = compute_qiyun_meta_v1(1992, 3, 12, 17, "갑", True)
    assert m["schema"] == "qiyun_v1"
    assert "birth_jd_ut" in m and "jie_boundary_jd_ut" in m


def test_qiyun_days_and_years_rounded_consistency():
    m = compute_qiyun_meta_v1(1992, 3, 12, 17, "갑", True)
    assert m["qiyun_years_float"] == round(m["qiyun_days"] / 3.0, 6)
