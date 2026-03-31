from scripts.generate_2026_monthly_kospi_btc_prophecy import _adjust_for_hold


def test_adjust_for_hold_shifts_to_defensive():
    up, neutral, down = _adjust_for_hold(40, 30, 30, True)
    assert up == 36
    assert neutral == 30
    assert down == 34


def test_adjust_for_hold_keeps_values_when_not_hold():
    up, neutral, down = _adjust_for_hold(40, 30, 30, False)
    assert (up, neutral, down) == (40, 30, 30)
