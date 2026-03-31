from scripts.broadcast_fact_safe_multilens_brief import _monthly_outlook_for_now


def test_monthly_outlook_shape():
    out = _monthly_outlook_for_now()
    if not out:
        assert out == {}
        return
    assert "month" in out
    assert "kospi_direction" in out
    assert "btc_direction" in out
