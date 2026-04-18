from scripts.saju_dual_verify import (
    VerifyInput,
    resolve_verify_input_from_utc,
    verify_dual_saju,
)


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
    assert doc["comparison"]["policy_interpretation"] == "confirmed"
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
    assert doc["comparison"]["policy_interpretation"] == "dst_review"
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


def test_dual_verify_zi_boundary_review_without_hour_pillar_mismatch():
    doc = verify_dual_saju(
        VerifyInput(
            year=1973,
            month=12,
            day=10,
            hour=23,
            minute=30,
            tz="Asia/Seoul",
            is_solar=True,
            is_male=True,
            secondary_day_rollover_policy="midnight_00",
        )
    )
    assert doc["comparison"]["status"] == "REVIEW"
    assert doc["comparison"]["policy_interpretation"] == "boundary_warning_only"
    assert "near_zi_boundary_window" in doc["comparison"]["reasons"]
    assert "pillar_mismatch_between_engines" not in doc["comparison"]["reasons"]
    assert doc["comparison"]["pillar_diffs"] == {}


def test_dual_verify_birth_instant_utc_path_matches_seoul_local():
    inp, meta = resolve_verify_input_from_utc(
        "1991-03-10T02:10:00Z",
        "Asia/Seoul",
        is_solar=True,
        is_male=True,
        secondary_day_rollover_policy="midnight_00",
    )
    assert inp.year == 1991 and inp.month == 3 and inp.day == 10
    assert inp.hour == 11 and inp.minute == 10
    assert inp.tz == "Asia/Seoul"
    assert meta["mode"] == "utc_instant"
    assert meta["iana_tz"] == "Asia/Seoul"
    doc = verify_dual_saju(inp, birth_resolution_meta=meta)
    assert doc["input"]["hour"] == 11
    assert doc["timezone_meta"]["birth_resolution"]["mode"] == "utc_instant"


def test_dual_verify_zi23_policy_confirmed_after_primary_rollover_alignment():
    doc = verify_dual_saju(
        VerifyInput(
            year=1973,
            month=12,
            day=10,
            hour=23,
            minute=31,
            tz="Asia/Seoul",
            is_solar=True,
            is_male=True,
            secondary_day_rollover_policy="zi_23",
        )
    )
    assert doc["comparison"]["status"] == "CONFIRMED"
    assert doc["comparison"]["is_confirmed"] is True
    assert doc["comparison"]["policy_interpretation"] == "confirmed"
    assert doc["comparison"]["pillar_diffs"] == {}
