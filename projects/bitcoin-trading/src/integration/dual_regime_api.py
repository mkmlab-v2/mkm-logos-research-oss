"""Dual regime evaluation API (primary regime + biblical auxiliary layer).

Bench/smoke callers: ``evaluate_dual_regime_and_market_shock``.
Policy SSOT: ``data/regimes/regime_fusion_policy.json`` (workspace-relative).
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class DualRegimeContext:
    """Result of dual-regime + market-shock evaluation."""

    risk_multiplier_cap: float
    interpretation: str
    resonance_count: int
    veto_triggered: bool
    market_shock_confirmed: bool


def _policy_path(workspace_root: Path) -> Path:
    return workspace_root / "data" / "regimes" / "regime_fusion_policy.json"


def _load_policy(workspace_root: Path) -> dict[str, Any]:
    path = _policy_path(workspace_root)
    if not path.is_file():
        return {
            "global": {
                "risk_multiplier_min": 0.5,
                "risk_multiplier_max": 1.2,
                "psi_thresholds": {"warning": 0.6, "crisis": 0.8},
            }
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_logos_resonance_to_cap(
    *,
    base_cap: float,
    risk_multiplier_min: float,
    risk_multiplier_max: float,
    vector_4d: Mapping[str, float],
    manuscript: str,
    workspace_root: Path,
    strength: float,
) -> tuple[float, list[str]]:
    """
    Optional Logos-4D bridge: adjust ``base_cap`` using GPU/CPU LogosEncoder when available.

    Returns (possibly unchanged cap, extra interpretation segments). On import/runtime
    failure the cap is unchanged and a ``logos_skip=...`` segment is returned.
    """
    root = str(workspace_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from tools.core.logos_encoder_gpu import (  # noqa: WPS433 — runtime import after path fix
            LogosEncoder,
            apply_logos_resonance_to_risk_cap,
            calculate_resonance,
            _TORCH_AVAILABLE,
        )
    except Exception as exc:  # pragma: no cover - wrong cwd
        return base_cap, [f"logos_skip=import:{type(exc).__name__}"]

    if not _TORCH_AVAILABLE:
        return base_cap, ["logos_skip=no_torch"]

    try:
        import torch

        enc = LogosEncoder()
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        logos_emb = enc.encode_text_to_logos_embedding(manuscript, device=dev)
        market_t = torch.tensor(
            [float(vector_4d.get(k, 0.25)) for k in ("S", "L", "K", "M")],
            dtype=torch.float32,
            device=logos_emb.device,
        ).unsqueeze(0)
        res_tensor = calculate_resonance(market_t, logos_emb)
        resonance = float(res_tensor.squeeze().item())
        adj = apply_logos_resonance_to_risk_cap(
            base_cap,
            resonance,
            risk_multiplier_min,
            risk_multiplier_max,
            strength=strength,
        )
        return adj.adjusted_cap, [
            f"logos_resonance={adj.resonance:.4f}",
            f"logos_delta={adj.delta:+.4f}",
        ]
    except Exception as exc:
        return base_cap, [f"logos_skip=runtime:{type(exc).__name__}"]


def _stress_score(
    psi_score: float,
    bible_risk_score: float,
    context_metrics: Mapping[str, float] | None,
) -> float:
    ctx = context_metrics or {}
    vals = [float(v) for v in ctx.values()] if ctx else [0.0]
    ctx_mean = sum(vals) / max(len(vals), 1)
    # Bounded stress in [0, 1]: high PSI, bible risk, and pathological context raise stress.
    raw = (
        max(0.0, psi_score - 0.5) * 1.25
        + min(1.0, max(0.0, bible_risk_score) * 0.35)
        + ctx_mean * 0.45
    )
    return max(0.0, min(1.0, raw))


def get_biblical_hypothesis_status(workspace_root: Path) -> dict[str, Any]:
    """Optional helper: surface whether hypothesis-only biblical triggers are allowed."""
    policy = _load_policy(workspace_root)
    g = policy.get("global") or {}
    return {
        "hypothesis_trigger_allowed": bool(g.get("hypothesis_trigger_allowed", False)),
        "policy_path": str(_policy_path(workspace_root)),
    }


def evaluate_dual_regime_and_market_shock(
    *,
    as_of: datetime,
    vector_4d: Mapping[str, float],
    psi_score: float,
    bible_risk_score: float,
    workspace_root: Path,
    context_metrics: Mapping[str, float] | None = None,
    logos_manuscript_text: str | None = None,
    logos_adjustment_strength: float = 0.12,
) -> DualRegimeContext:
    """Combine PSI, auxiliary bible-risk, and context into a risk cap and shock flags.

    This is a **bench/safe** implementation: no live orders; uses JSON policy only.
    """
    _ = as_of  # timestamp reserved for future Chronos / regime_map lookups
    policy = _load_policy(workspace_root)
    g = policy.get("global") or {}
    rmin = float(g.get("risk_multiplier_min", 0.5))
    rmax = float(g.get("risk_multiplier_max", 1.2))
    warn = float((g.get("psi_thresholds") or {}).get("warning", 0.6))
    crisis = float((g.get("psi_thresholds") or {}).get("crisis", 0.8))

    # Resonance: count how many 4D axes are "active" (deviation from neutral 0.25)
    resonance_count = 0
    for key in ("S", "L", "K", "M"):
        v = float(vector_4d.get(key, 0.25))
        if abs(v - 0.25) >= 0.05:
            resonance_count += 1

    stress = _stress_score(psi_score, bible_risk_score, context_metrics)
    cap = rmax - stress * (rmax - rmin)
    cap = max(rmin, min(rmax, cap))

    logos_segments: list[str] = []
    if logos_manuscript_text and str(logos_manuscript_text).strip():
        cap, logos_segments = _apply_logos_resonance_to_cap(
            base_cap=cap,
            risk_multiplier_min=rmin,
            risk_multiplier_max=rmax,
            vector_4d=vector_4d,
            manuscript=str(logos_manuscript_text).strip(),
            workspace_root=workspace_root,
            strength=float(logos_adjustment_strength),
        )

    shock = psi_score >= crisis and stress >= 0.55
    veto = psi_score >= crisis and bible_risk_score >= 1.0 and (context_metrics or {})

    parts = [
        f"PSI={psi_score:.2f} (warn>{warn:.2f}, crisis>{crisis:.2f})",
        f"bible_risk={bible_risk_score:.2f}",
        f"stress={stress:.2f}",
        f"cap={cap:.2f}",
    ]
    if logos_segments:
        parts.extend(logos_segments)
    interpretation = "dual_regime: " + "; ".join(parts)

    return DualRegimeContext(
        risk_multiplier_cap=cap,
        interpretation=interpretation,
        resonance_count=resonance_count,
        veto_triggered=bool(veto),
        market_shock_confirmed=bool(shock),
    )
