from __future__ import annotations

from scripts.experimental.codebook_runtime_pack.build_report_schema_v2_quality_alert import (
    compute_v2_quality_severity,
)


def test_severity_fail_solo_ceiling() -> None:
    sev, codes = compute_v2_quality_severity(
        grounded_false_rate=0.3,
        gate="pass",
        streak_alert=False,
        fail_solo_grounded_false_rate=0.25,
        fail_pair_min_grounded_false_rate=0.10,
        fail_on_streak_and_gate_warn=True,
        warn_min_grounded_false_rate=0.08,
    )
    assert sev == "FAIL"
    assert "fail_grounded_false_rate_ge_solo_ceiling" in codes


def test_severity_fail_streak_and_rate_pair() -> None:
    sev, codes = compute_v2_quality_severity(
        grounded_false_rate=0.12,
        gate="pass",
        streak_alert=True,
        fail_solo_grounded_false_rate=0.25,
        fail_pair_min_grounded_false_rate=0.10,
        fail_on_streak_and_gate_warn=False,
        warn_min_grounded_false_rate=0.08,
    )
    assert sev == "FAIL"
    assert "fail_delta_streak_with_grounded_false_rate_ge_pair_min" in codes


def test_severity_fail_streak_and_gate_warn() -> None:
    sev, codes = compute_v2_quality_severity(
        grounded_false_rate=0.0,
        gate="warn",
        streak_alert=True,
        fail_solo_grounded_false_rate=0.25,
        fail_pair_min_grounded_false_rate=0.10,
        fail_on_streak_and_gate_warn=True,
        warn_min_grounded_false_rate=0.08,
    )
    assert sev == "FAIL"
    assert "fail_delta_streak_and_label_kpi_gate_warn" in codes


def test_severity_warn_streak_only() -> None:
    sev, codes = compute_v2_quality_severity(
        grounded_false_rate=0.0,
        gate="pass",
        streak_alert=True,
        fail_solo_grounded_false_rate=0.25,
        fail_pair_min_grounded_false_rate=0.10,
        fail_on_streak_and_gate_warn=False,
        warn_min_grounded_false_rate=0.08,
    )
    assert sev == "WARN"
    assert "warn_delta_streak_alert" in codes


def test_severity_info_clean() -> None:
    sev, codes = compute_v2_quality_severity(
        grounded_false_rate=0.0,
        gate="pass",
        streak_alert=False,
        fail_solo_grounded_false_rate=0.25,
        fail_pair_min_grounded_false_rate=0.10,
        fail_on_streak_and_gate_warn=True,
        warn_min_grounded_false_rate=0.08,
    )
    assert sev == "INFO"
    assert codes == []
