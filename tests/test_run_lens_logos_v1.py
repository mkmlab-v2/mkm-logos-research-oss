"""Regression for the falsification-informed logos lens direction_score ({S,K} only)."""
from __future__ import annotations

from scripts.run_lens_logos import (
    FALSIFIED_AXES_EXCLUDED,
    SURVIVING_AXES,
    _scores_from_vecs,
)


def test_surviving_and_falsified_axis_constants():
    assert SURVIVING_AXES == ("S", "K")
    assert set(FALSIFIED_AXES_EXCLUDED) == {"L", "M"}
    assert not (set(SURVIVING_AXES) & set(FALSIFIED_AXES_EXCLUDED))


def test_direction_uses_only_S_and_K():
    # S=K=1.0 -> mean_surviving 1.0 -> (1.0-0.5)*2 = 1.0, regardless of L,M
    d, c = _scores_from_vecs([{"S": 1.0, "K": 1.0, "L": 0.0, "M": 0.0}])
    assert d == 1.0
    d2, _ = _scores_from_vecs([{"S": 0.5, "K": 0.5, "L": 0.0, "M": 0.0}])
    assert d2 == 0.0


def test_direction_invariant_to_falsified_axes():
    base = [{"S": 0.7, "K": 0.3, "L": 0.1, "M": 0.9}]
    flipped = [{"S": 0.7, "K": 0.3, "L": 0.9, "M": 0.1}]  # only L,M changed
    assert _scores_from_vecs(base)[0] == _scores_from_vecs(flipped)[0]


def test_equal_weight_not_k_centric():
    # swapping S and K values yields the same direction (equal weight, symmetric)
    a = _scores_from_vecs([{"S": 0.9, "K": 0.1, "L": 0.5, "M": 0.5}])[0]
    b = _scores_from_vecs([{"S": 0.1, "K": 0.9, "L": 0.5, "M": 0.5}])[0]
    assert a == b


def test_empty_fallback():
    assert _scores_from_vecs([]) == (0.0, 0.25)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
