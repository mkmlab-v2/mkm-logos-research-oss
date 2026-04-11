# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.55, L:0.5, K:0.6, M:0.45}
# Balance: 83
# Purpose: zone_a baseline must_keep + boming jiju overlay smoke test.
# Keywords: zone_a_scm, baseline, boming
from __future__ import annotations

from types import SimpleNamespace

from scripts.core.scm_boming_jiju_lexicon_v1 import DEFAULT_LEXICON_PATH
from scripts.report_zone_a_scm_baseline_v1 import simulate_effective_must_keep_a_extreme


def test_boming_overlay_adds_hits_when_term_in_text() -> None:
    route = SimpleNamespace(must_keep_hard_terms=["x"], must_keep_soft_terms=["y"])
    raw = "임상 기록 호산지기 유지"
    eff, _meta, eff_b, bmeta = simulate_effective_must_keep_a_extreme(
        raw,
        route,
        cb_path=None,
        boming_path=DEFAULT_LEXICON_PATH,
    )
    assert bmeta and bmeta.get("status") == "ok"
    assert "호산지기" in eff_b
    assert len(eff_b) > len(eff)
