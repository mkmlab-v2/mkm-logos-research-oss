from __future__ import annotations

from pathlib import Path


def test_constitution_contains_btrack_carveout_and_guardrails() -> None:
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "final" / "CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
    text = p.read_text(encoding="utf-8")

    assert "### 3.7 B-track 재조정 수집 완화 규칙 (연구 전용 carve-out)" in text
    assert "`research_only=true`" in text
    assert "`promotion_required=true`" in text
    assert "dual_regime_api.py" in text
    assert "게마트리아 수치·재조정 prior의 본선 하드코딩" in text
    assert "§8 Promotion Loop" in text
