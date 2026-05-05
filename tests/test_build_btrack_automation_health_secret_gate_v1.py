from __future__ import annotations

import scripts.build_btrack_automation_health_snapshot_v1 as mod


def test_is_secret_exposure_survey_ok_requires_ok_severity_and_zero_counts() -> None:
    assert mod.is_secret_exposure_survey_ok(None) is False
    assert mod.is_secret_exposure_survey_ok({}) is False
    assert mod.is_secret_exposure_survey_ok({"summary": {"severity": "ok", "exact_match_count": 0, "pattern_match_count": 0}}) is True
    assert mod.is_secret_exposure_survey_ok({"summary": {"severity": "warning", "exact_match_count": 0, "pattern_match_count": 0}}) is False
    assert mod.is_secret_exposure_survey_ok({"summary": {"severity": "ok", "exact_match_count": 1, "pattern_match_count": 0}}) is False
