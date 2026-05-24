"""compression_profile economy | fidelity | literal — Fact-Lock mapping."""

from __future__ import annotations

import pytest

from scripts.compression_profile_v1 import (
    profile_evaluate_report_kwargs,
    profile_evaluate_report_kwargs_v2,
    profile_meta,
)


def test_economy_bridge_off() -> None:
    kw = profile_evaluate_report_kwargs("economy")
    assert kw["apply_gematria_4d_bridge_policy"] is False
    assert kw["include_gematria_4d_bridge"] is False


def test_economy_wire_bench_aligned_kwargs() -> None:
    kw = profile_evaluate_report_kwargs_v2("economy", graph_wire_selective_bridge=True)
    assert kw["apply_gematria_4d_bridge_policy"] is False
    assert kw["include_gematria_4d_bridge"] is True
    assert kw.get("bench_aligned") == "comp_atom05_full_v2_wire_selective"


def test_economy_no_wire_uses_profile_only() -> None:
    kw = profile_evaluate_report_kwargs_v2("economy", graph_wire_selective_bridge=False)
    assert kw["include_gematria_4d_bridge"] is False
    assert "bench_aligned" not in kw


def test_fidelity_bridge_on() -> None:
    kw = profile_evaluate_report_kwargs("fidelity")
    assert kw["apply_gematria_4d_bridge_policy"] is True
    assert kw["include_gematria_4d_bridge"] is True


def test_literal_conservative_caps() -> None:
    kw = profile_evaluate_report_kwargs("literal")
    assert kw["apply_gematria_4d_bridge_policy"] is False
    assert kw["strategy"] == "C"
    assert kw["intensity"] == "high"
    assert kw["general_max_saving_rate"] == 0.28


def test_profile_meta_points_at_comp_atom01_for_economy() -> None:
    m = profile_meta("economy")
    assert m["compression_profile"] == "economy"
    assert "comp_atom01_ab_summary" in m["bench_ssot_artifact"]
    assert m["apply_gematria_4d_bridge_policy"] is False
    # 41658 production SSOT (Policy A); frozen MS paste 0.890 = archived 41775 only.
    assert m["headline_bench_jaccard"] == pytest.approx(0.8727418293565741)
