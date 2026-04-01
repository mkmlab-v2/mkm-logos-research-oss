from scripts.broadcast_fact_safe_multilens_brief import _monthly_outlook_for_now, _next_month_risk_hint


def test_monthly_outlook_shape():
    out = _monthly_outlook_for_now()
    if not out:
        assert out == {}
        return
    assert "month" in out
    assert "kospi_direction" in out
    assert "btc_direction" in out
    assert "price_output_locked" in out
    assert "lock_reason" in out
    assert "risk_profile_mode" in out
    assert "risk_position_scale_cap" in out


def test_next_month_risk_hint_shape():
    hint = _next_month_risk_hint()
    if hint is None:
        assert hint is None
        return
    assert "선행 리스크" in hint
