from scripts.core.mkm12_singular_core import CoreInput, compute_core_score, round_to_grid


def test_round_to_grid_quarter_steps():
    assert round_to_grid(0.62) == 0.5
    assert round_to_grid(0.63) == 0.75


def test_compute_core_score_hold_band():
    out = compute_core_score(CoreInput(s=0.5, l=0.5, k=0.5, m=0.5))
    assert out["decision"] == "HOLD"
    assert out["score_grid"] == 0.0


def test_compute_core_score_long_pass():
    out = compute_core_score(CoreInput(s=1.0, l=1.0, k=1.0, m=1.0))
    assert out["decision"] == "PASS_LONG"
    assert out["score_grid"] >= 0.75
