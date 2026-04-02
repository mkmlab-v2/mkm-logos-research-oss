"""Dual regime evaluation API (primary regime + biblical auxiliary layer).

Bench/smoke callers: ``evaluate_dual_regime_and_market_shock``.
Policy SSOT: ``data/regimes/regime_fusion_policy.json`` (workspace-relative).

B-track 16-state experiment (JSONL / schema) does **not** feed risk caps unless
explicitly wired elsewhere; ``get_myeongni_16_state_experiment_ssot`` only
surfaces paths for observability and HTTP metadata.
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


def _select_gate_profile(
    *,
    policy: Mapping[str, Any],
    gate_profile: str | None,
) -> dict[str, Any]:
    """Resolve gate profile from policy with safe fallback."""
    g = policy.get("global") or {}
    profiles = g.get("gate_profiles") if isinstance(g.get("gate_profiles"), Mapping) else {}
    default_name = str(g.get("default_gate_profile", "balanced")).strip().lower()
    requested = (str(gate_profile).strip().lower() if gate_profile else default_name)
    selected = profiles.get(requested) if isinstance(profiles, Mapping) else None
    if not isinstance(selected, Mapping):
        selected = profiles.get(default_name) if isinstance(profiles, Mapping) else None
    if not isinstance(selected, Mapping):
        # Backward-compatible fallback to global flat keys.
        selected = {
            "risk_multiplier_min": g.get("risk_multiplier_min", 0.5),
            "risk_multiplier_max": g.get("risk_multiplier_max", 1.2),
            "psi_thresholds": g.get("psi_thresholds", {"warning": 0.6, "crisis": 0.8}),
            "shock_stress_threshold": g.get("shock_stress_threshold", 0.55),
            "veto_bible_risk_threshold": g.get("veto_bible_risk_threshold", 1.0),
            "veto_requires_context": g.get("veto_requires_context", True),
        }
    return {"name": requested, "config": dict(selected)}


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
            apply_logos_resonance_to_risk_cap,
            calculate_resonance,
            get_logos_encoder,
            _TORCH_AVAILABLE,
        )
    except Exception as exc:  # pragma: no cover - wrong cwd
        return base_cap, [f"logos_skip=import:{type(exc).__name__}"]

    if not _TORCH_AVAILABLE:
        return base_cap, ["logos_skip=no_torch"]

    try:
        import torch

        enc = get_logos_encoder()
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


def _normalize_state_id(state_id: Any) -> int | None:
    """Normalize optional state id to 1..16, else None."""
    try:
        sid = int(state_id)
    except (TypeError, ValueError):
        return None
    if 1 <= sid <= 16:
        return sid
    return None


def _apply_myeongni_state_defensive_clamp(
    *,
    cap: float,
    state_id: Any,
    policy_global: Mapping[str, Any],
    risk_multiplier_min: float,
    risk_multiplier_max: float,
) -> tuple[float, str | None]:
    """Apply optional state clamp that can only tighten risk (never loosen)."""
    enabled = bool(policy_global.get("myeongni_state_defensive_clamp_enabled", False))
    if not enabled:
        return cap, None

    sid = _normalize_state_id(state_id)
    if sid is None:
        return cap, "state_clamp_skip=invalid_state_id"

    cap_map = policy_global.get("myeongni_state_risk_cap_map")
    mapped = cap_map.get(str(sid)) if isinstance(cap_map, Mapping) else None
    raw_state_cap = mapped if mapped is not None else policy_global.get("myeongni_state_risk_cap_default")
    if raw_state_cap is None:
        return cap, "state_clamp_skip=no_state_cap"
    try:
        state_cap = float(raw_state_cap)
    except (TypeError, ValueError):
        return cap, "state_clamp_skip=invalid_state_cap"

    bounded_state_cap = max(risk_multiplier_min, min(risk_multiplier_max, state_cap))
    clamped = min(cap, bounded_state_cap)
    if clamped < cap:
        return clamped, f"state_clamp=on;state_id={sid};state_cap={bounded_state_cap:.4f}"
    return cap, f"state_clamp=on;state_id={sid};state_cap_noop={bounded_state_cap:.4f}"


def get_biblical_hypothesis_status(workspace_root: Path) -> dict[str, Any]:
    """Optional helper: surface whether hypothesis-only biblical triggers are allowed."""
    policy = _load_policy(workspace_root)
    g = policy.get("global") or {}
    return {
        "hypothesis_trigger_allowed": bool(g.get("hypothesis_trigger_allowed", False)),
        "policy_path": str(_policy_path(workspace_root)),
    }


def get_myeongni_16_state_experiment_ssot(workspace_root: Path) -> dict[str, Any]:
    """Read-only B-track Fact-Lock paths (schema, ledger CLI, JSONL).

    Does not read ledger contents or alter ``evaluate_dual_regime_and_market_shock``.
    Align with ``docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`` §3.1.
    """
    root = workspace_root.resolve()
    schema = root / "docs" / "final" / "MYEONGNI_16_STATE_EXPERIMENT_JSON_SCHEMA.json"
    ledger_cli = root / "scripts" / "myeongni_16_state_experiment_ledger.py"
    jsonl = root / "data" / "myeongni" / "myeongni_16_state_experiment_v1.jsonl"
    sample_jsonl = root / "data" / "myeongni" / "myeongni_16_state_experiment_v1.sample.jsonl"
    return {
        "schema_path": str(schema),
        "ledger_cli_path": str(ledger_cli),
        "jsonl_path": str(jsonl),
        "sample_jsonl_path": str(sample_jsonl),
        "schema_exists": schema.is_file(),
        "ledger_cli_exists": ledger_cli.is_file(),
        "jsonl_exists": jsonl.is_file(),
        "sample_jsonl_exists": sample_jsonl.is_file(),
    }


def get_fused_week_contract_ssot(workspace_root: Path) -> dict[str, Any]:
    """Read-only helper exposing fused week contract latest snapshot path/content."""
    path = workspace_root / "docs" / "final" / "artifacts" / "fused_paper_cycle_weekly_latest.json"
    payload: dict[str, Any] = {}
    if path.is_file():
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                payload = obj
        except Exception:
            payload = {}
    return {
        "schema": "fused_week_contract_ssot_v1",
        "path": str(path),
        "exists": path.is_file(),
        "week_contract": payload.get("week_contract"),
        "decision": payload.get("decision"),
        "toe_score": payload.get("toe_score"),
        "generated_at_utc": payload.get("generated_at_utc"),
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
    state_id: int | None = None,
    gate_profile: str | None = None,
) -> DualRegimeContext:
    """Combine PSI, auxiliary bible-risk, and context into a risk cap and shock flags.

    This is a **bench/safe** implementation: no live orders; uses JSON policy only.
    """
    _ = as_of  # timestamp reserved for future Chronos / regime_map lookups
    policy = _load_policy(workspace_root)
    g = policy.get("global") or {}
    gate = _select_gate_profile(policy=policy, gate_profile=gate_profile)
    gate_cfg = gate["config"]

    rmin = float(gate_cfg.get("risk_multiplier_min", g.get("risk_multiplier_min", 0.5)))
    rmax = float(gate_cfg.get("risk_multiplier_max", g.get("risk_multiplier_max", 1.2)))
    psi_cfg = gate_cfg.get("psi_thresholds") if isinstance(gate_cfg.get("psi_thresholds"), Mapping) else {}
    warn = float(psi_cfg.get("warning", (g.get("psi_thresholds") or {}).get("warning", 0.6)))
    crisis = float(psi_cfg.get("crisis", (g.get("psi_thresholds") or {}).get("crisis", 0.8)))
    shock_stress_threshold = float(gate_cfg.get("shock_stress_threshold", 0.55))
    veto_bible_risk_threshold = float(gate_cfg.get("veto_bible_risk_threshold", 1.0))
    veto_requires_context = bool(gate_cfg.get("veto_requires_context", True))

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

    cap, state_segment = _apply_myeongni_state_defensive_clamp(
        cap=cap,
        state_id=state_id,
        policy_global=g,
        risk_multiplier_min=rmin,
        risk_multiplier_max=rmax,
    )

    has_context = bool(context_metrics or {})
    context_ok = has_context if veto_requires_context else True
    shock = psi_score >= crisis and stress >= shock_stress_threshold
    veto = psi_score >= crisis and bible_risk_score >= veto_bible_risk_threshold and context_ok

    parts = [
        f"gate_profile={gate['name']}",
        f"PSI={psi_score:.2f} (warn>{warn:.2f}, crisis>{crisis:.2f})",
        f"bible_risk={bible_risk_score:.2f}",
        f"stress={stress:.2f}",
        f"cap={cap:.2f}",
    ]
    if logos_segments:
        parts.extend(logos_segments)
    if state_segment:
        parts.append(state_segment)
    interpretation = "dual_regime: " + "; ".join(parts)

    return DualRegimeContext(
        risk_multiplier_cap=cap,
        interpretation=interpretation,
        resonance_count=resonance_count,
        veto_triggered=bool(veto),
        market_shock_confirmed=bool(shock),
    )
