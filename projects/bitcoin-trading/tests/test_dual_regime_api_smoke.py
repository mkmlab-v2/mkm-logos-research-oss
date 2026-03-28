"""Dual Regime API Fact-Lock: parametrized FGI boundaries, shock gate, policy floor.

Policy SSOT: ``data/regimes/regime_fusion_policy.json`` (workspace root).

FGI (Fear & Greed 0–100) is injected as ``context_metrics["fear_greed_index"] = fgi / 100.0``
so ``_stress_score`` context mean matches documented bench semantics (single metric).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

# bitcoin-trading root (same layout as scripts/run_forced_watch_alert_test.py)
_BT_ROOT = Path(__file__).resolve().parents[1]
if str(_BT_ROOT) not in sys.path:
    sys.path.insert(0, str(_BT_ROOT))

from src.integration.dual_regime_api import (  # noqa: E402
    _policy_path,
    _stress_score,
    evaluate_dual_regime_and_market_shock,
)


def _workspace_root() -> Path:
    """Repo workspace root: parent of ``projects/bitcoin-trading``."""
    return Path(__file__).resolve().parents[3]


def _load_global_policy() -> dict:
    path = _policy_path(_workspace_root())
    assert path.is_file(), f"policy SSOT must exist: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("global") or {}


# --- Expected cap / shock (same formulas as ``dual_regime_api``) ---


def _expected_cap(
    stress: float,
    rmin: float,
    rmax: float,
) -> float:
    cap = rmax - stress * (rmax - rmin)
    return max(rmin, min(rmax, cap))


def _expected_shock(psi_score: float, crisis: float, stress: float) -> bool:
    return psi_score >= crisis and stress >= 0.55


# ---------------------------------------------------------------------------
# 1) Original bench parity (regime_integrity marker for report collector)
# ---------------------------------------------------------------------------


@pytest.mark.regime_integrity
def test_forced_watch_inputs_match_bench_script() -> None:
    """Same inputs as ``scripts/run_forced_watch_alert_test.py`` → cap 0.5, WATCH path."""
    workspace_root = _workspace_root()
    policy_path = _policy_path(workspace_root)
    assert policy_path.is_file(), f"policy SSOT must exist: {policy_path}"

    ctx = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=0.9,
        bible_risk_score=1.2,
        workspace_root=workspace_root,
        context_metrics={
            "myeongri_conflict_score": 0.8,
            "sasang_pathology_score": 0.8,
        },
    )

    # TEMP: intentional mismatch to verify CI autopsy artifacts (revert to 0.5 after verification).
    assert ctx.risk_multiplier_cap == 0.6
    triggered = ctx.risk_multiplier_cap < 1.0
    assert triggered is True
    assert ctx.resonance_count == 0
    assert "cap=0.50" in ctx.interpretation or "cap=0.5" in ctx.interpretation


# ---------------------------------------------------------------------------
# 2) FGI boundaries (single normalized metric; PSI neutral, bible 0)
# ---------------------------------------------------------------------------


@pytest.mark.regime_integrity
@pytest.mark.parametrize(
    "fgi",
    [0.0, 24.9, 25.0, 74.9, 75.0, 100.0],
    ids=["fgi_0", "fgi_24_9", "fgi_25", "fgi_74_9", "fgi_75", "fgi_100"],
)
def test_fgi_boundaries_cap_matches_formula(fgi: float) -> None:
    """FGI-only path: ``fear_greed_index`` in [0,1] drives context mean; cap follows policy."""
    g = _load_global_policy()
    rmin = float(g["risk_multiplier_min"])
    rmax = float(g["risk_multiplier_max"])
    crisis = float((g.get("psi_thresholds") or {}).get("crisis", 0.8))

    workspace_root = _workspace_root()
    psi = 0.5
    bible = 0.0
    ctx_metrics = {"fear_greed_index": fgi / 100.0}

    stress = _stress_score(psi, bible, ctx_metrics)
    expected_cap = _expected_cap(stress, rmin, rmax)

    out = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=psi,
        bible_risk_score=bible,
        workspace_root=workspace_root,
        context_metrics=ctx_metrics,
    )

    assert out.risk_multiplier_cap == pytest.approx(expected_cap, rel=0, abs=1e-9)
    assert out.market_shock_confirmed == _expected_shock(psi, crisis, stress)


# ---------------------------------------------------------------------------
# 3) Market shock: PSI crisis gate + stress >= 0.55
# ---------------------------------------------------------------------------


@pytest.mark.regime_integrity
@pytest.mark.parametrize(
    "aux_ctx,expect_shock",
    [
        ({"liquidity_stress": 0.38}, False),  # stress ~0.546 < 0.55
        ({"liquidity_stress": 0.40}, True),  # stress ~0.555 >= 0.55
    ],
    ids=["shock_below_stress_gate", "shock_above_stress_gate"],
)
def test_shock_requires_crisis_psi_and_stress_threshold(
    aux_ctx: dict[str, float],
    expect_shock: bool,
) -> None:
    """``market_shock_confirmed`` flips when stress crosses 0.55 with PSI at crisis."""
    workspace_root = _workspace_root()
    g = _load_global_policy()
    crisis = float((g.get("psi_thresholds") or {}).get("crisis", 0.8))
    psi = crisis  # exactly at crisis
    bible = 0.0
    stress = _stress_score(psi, bible, aux_ctx)

    out = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=psi,
        bible_risk_score=bible,
        workspace_root=workspace_root,
        context_metrics=aux_ctx,
    )
    assert out.market_shock_confirmed is expect_shock
    assert out.market_shock_confirmed == _expected_shock(psi, crisis, stress)


@pytest.mark.regime_integrity
def test_shock_false_when_psi_below_crisis_even_if_stress_high() -> None:
    """PSI below crisis cannot confirm shock (bench rule)."""
    workspace_root = _workspace_root()
    g = _load_global_policy()
    crisis = float((g.get("psi_thresholds") or {}).get("crisis", 0.8))
    psi = crisis - 0.01
    ctx = {"liquidity_stress": 1.0, "extra": 1.0}
    stress = _stress_score(psi, 0.0, ctx)
    assert stress >= 0.55

    out = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=psi,
        bible_risk_score=0.0,
        workspace_root=workspace_root,
        context_metrics=ctx,
    )
    assert out.market_shock_confirmed is False
    assert _expected_shock(psi, crisis, stress) is False


@pytest.mark.regime_integrity
def test_risk_multiplier_cap_responds_to_shock_path_stress() -> None:
    """Higher auxiliary stress at same PSI lowers cap (risk_multiplier_cap change)."""
    workspace_root = _workspace_root()
    psi = 0.85
    low = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=psi,
        bible_risk_score=0.0,
        workspace_root=workspace_root,
        context_metrics={"liquidity_stress": 0.1},
    )
    high = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=psi,
        bible_risk_score=0.0,
        workspace_root=workspace_root,
        context_metrics={"liquidity_stress": 0.95},
    )
    assert high.risk_multiplier_cap < low.risk_multiplier_cap


# ---------------------------------------------------------------------------
# 4) Policy JSON risk_multiplier_min as hard floor
# ---------------------------------------------------------------------------


@pytest.mark.regime_integrity
def test_risk_multiplier_min_is_hard_floor_from_policy() -> None:
    """Maximal stress clamps cap to ``risk_multiplier_min`` from policy JSON."""
    g = _load_global_policy()
    rmin = float(g["risk_multiplier_min"])
    workspace_root = _workspace_root()

    out = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=1.0,
        bible_risk_score=3.0,
        workspace_root=workspace_root,
        context_metrics={"liquidity_stress": 1.0, "s1": 1.0, "s2": 1.0},
    )
    assert out.risk_multiplier_cap == rmin
    assert out.risk_multiplier_cap == pytest.approx(rmin, rel=0, abs=1e-9)


@pytest.mark.regime_integrity
def test_risk_multiplier_max_when_zero_stress() -> None:
    """Minimal stress yields cap at ``risk_multiplier_max``."""
    g = _load_global_policy()
    rmax = float(g["risk_multiplier_max"])
    workspace_root = _workspace_root()

    out = evaluate_dual_regime_and_market_shock(
        as_of=datetime(2026, 3, 29, 12, 0, 0),
        vector_4d={"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25},
        psi_score=0.5,
        bible_risk_score=0.0,
        workspace_root=workspace_root,
        context_metrics={"fear_greed_index": 0.0},
    )
    assert out.risk_multiplier_cap == pytest.approx(rmax, rel=0, abs=1e-9)
