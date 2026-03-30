from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
W4_PATH = ROOT / "docs" / "final" / "artifacts" / "W4_PROMOTION_DECISION_FINAL.md"


def test_w4_promotion_decision_contains_aux_non_gating_section() -> None:
    text = W4_PATH.read_text(encoding="utf-8")
    assert "Updated at UTC:" in text
    assert "auxiliary adapter (non-gating):" in text
    assert "aux_adapter_version =" in text
    assert "top_n_aux_non_gating_present =" in text
    assert "ranking_or_gate_participation = false (metadata only)" in text
