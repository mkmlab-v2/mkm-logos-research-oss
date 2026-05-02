# @MKM12-METADATA
# Type: Logic
# Purpose: Logos dual_regime interpretation_snippet validation (Phase A-1)
# Keywords: dual_regime, multilens, operational_brief

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.core.logos_dual_regime_interpretation_snippet_v1 import (  # noqa: E402
    PREFIX,
    build_interpretation_snippet,
    clip_snippet,
    validate_dual_regime_interpretation,
)


def test_validate_accepts_api_shaped_string() -> None:
    s = (
        f"{PREFIX}gate_profile=balanced; PSI=0.90 (warn>0.60, crisis>0.80); "
        "bible_risk=1.20; stress=1.00; cap=0.50; state_clamp_skip=invalid_state_id"
    )
    ok, err = validate_dual_regime_interpretation(s)
    assert ok and err is None


def test_validate_rejects_injection() -> None:
    s = f"{PREFIX}Buy BTC now; cap=0.5"
    ok, err = validate_dual_regime_interpretation(s)
    assert not ok
    assert err and "disallowed" in err


def test_clip_respects_max() -> None:
    long = "x" * 1000
    out = clip_snippet(long, 20)
    assert len(out) == 20
    assert out.endswith("…")


def test_build_snippet_uses_fallback_when_invalid() -> None:
    snippet, meta = build_interpretation_snippet("not a dual regime string", workspace_root=_ROOT)
    assert meta["validation_ok"] is False
    assert meta["snippet_source"] == "fallback_noncompliant"
    assert "interpretation_snippet_fallback" in snippet
    assert "audit_sha256_prefix=" in snippet


def test_rules_json_exists() -> None:
    p = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_DUAL_REGIME_INTERPRETATION_SNIPPET_RULES_V1.json"
    assert p.is_file()
