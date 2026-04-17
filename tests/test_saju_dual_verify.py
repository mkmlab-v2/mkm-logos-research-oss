from scripts.saju_dual_verify import VerifyInput, verify_dual_saju


def test_dual_verify_reports_confirmed_after_month_hotfix():
    doc = verify_dual_saju(
        VerifyInput(
            year=1973,
            month=12,
            day=10,
            hour=4,
            minute=30,
            tz="Asia/Seoul",
            is_solar=True,
            is_male=True,
            secondary_day_rollover_policy="midnight_00",
        )
    )
    assert doc["comparison"]["status"] == "CONFIRMED"
    assert doc["comparison"]["is_confirmed"] is True
    assert doc["comparison"]["pillar_diffs"] == {}
    assert doc["comparison"]["hour_branch_check"]["expected_hour_branch"] == "인"
    assert doc["comparison"]["hour_branch_check"]["matches_expected"] is True


def test_dual_verify_has_timezone_metadata():
    doc = verify_dual_saju(
        VerifyInput(
            year=2026,
            month=4,
            day=17,
            hour=4,
            minute=30,
            tz="Asia/Seoul",
            is_solar=True,
            is_male=True,
            secondary_day_rollover_policy="midnight_00",
        )
    )
    assert doc["timezone_meta"]["offset_seconds"] == 32400
    assert doc["timezone_meta"]["dst_seconds"] == 0
    assert doc["timezone_meta"]["dst_transition_check"]["is_ambiguous_local_time"] is False
    assert doc["timezone_meta"]["dst_transition_check"]["is_nonexistent_local_time"] is False
    assert "boundary_risk_check" in doc["timezone_meta"]


def test_dual_verify_marks_review_for_ambiguous_dst_local_time():
    doc = verify_dual_saju(
        VerifyInput(
            year=2021,
            month=11,
            day=7,
            hour=1,
            minute=30,
            tz="America/New_York",
            is_solar=True,
            is_male=True,
            secondary_day_rollover_policy="midnight_00",
        )
    )
    assert doc["timezone_meta"]["dst_transition_check"]["is_ambiguous_local_time"] is True
    assert doc["comparison"]["status"] == "REVIEW"
    assert "ambiguous_local_time_due_to_dst" in doc["comparison"]["reasons"]


def test_dual_verify_marks_review_near_solar_term_anchor_day():
    doc = verify_dual_saju(
        VerifyInput(
            year=1973,
            month=12,
            day=7,
            hour=4,
            minute=30,
            tz="Asia/Seoul",
            is_solar=True,
            is_male=True,
            secondary_day_rollover_policy="midnight_00",
        )
    )
    assert doc["timezone_meta"]["boundary_risk_check"]["is_boundary_risk"] is True
    assert "near_solar_term_anchor_day" in doc["comparison"]["reasons"]
    assert doc["comparison"]["status"] == "REVIEW"
