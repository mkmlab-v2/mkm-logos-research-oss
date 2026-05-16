"""Sync Fact-Safe prophecy risk profile into trader risk_profile_latest.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = ROOT / "scripts"
if _SCRIPTS_DIR.is_dir() and str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from workspace_maintenance_gate import is_workspace_maintenance_active  # noqa: E402
DEFAULT_PROPHECY = ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
DEFAULT_OUT = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
DEFAULT_GOVERNANCE = ROOT / "docs" / "final" / "artifacts" / "integrated_governance_v1_latest.json"
DEFAULT_TRINITY_PREDICTION = ROOT / "docs" / "final" / "artifacts" / "trinity_3lens_prediction_latest.json"
DEFAULT_TRINITY_DAILY_SCORE = ROOT / "docs" / "final" / "artifacts" / "trinity_daily_score_latest.json"
DEFAULT_TRINITY_WEIGHTS = ROOT / "docs" / "final" / "artifacts" / "trinity_lens_weights_latest.json"
DEFAULT_TRINITY_PREDICTION_BTC = ROOT / "docs" / "final" / "artifacts" / "trinity_3lens_prediction_btc_latest.json"
DEFAULT_TRINITY_DAILY_SCORE_BTC = ROOT / "docs" / "final" / "artifacts" / "trinity_daily_score_btc_latest.json"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _optional_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _would_downgrade_n8n_metadata(existing: dict[str, Any], new_source: str) -> bool:
    """True if existing profile is n8n-tagged but new_source would drop the n8n.* prefix."""
    old_src = str(existing.get("source") or "").strip()
    if not old_src.startswith("n8n."):
        return False
    new_src = str(new_source or "").strip()
    return not new_src.startswith("n8n.")


def _governance_caps(governance: dict[str, Any]) -> dict[str, Any]:
    regime = str(governance.get("final_regime") or "HOLD").upper()
    is_fallback = bool(governance.get("is_fallback"))
    final_action_allowed = bool(governance.get("final_action_allowed", True))
    final_score = float(governance.get("final_score") or 0.0)
    veto_reason_codes = governance.get("veto_reason_codes")
    if not isinstance(veto_reason_codes, list):
        veto_reason_codes = []

    # Conservative bridge profile: ATTACK keeps base sizing, HOLD/DEFENSE tighten it.
    caps_by_regime: dict[str, tuple[float, float]] = {
        "ATTACK": (1.00, 1.00),
        "HOLD": (0.65, 0.70),
        "DEFENSE": (0.35, 0.50),
    }
    pos_cap_mul, lev_cap_mul = caps_by_regime.get(regime, caps_by_regime["HOLD"])
    if is_fallback:
        pos_cap_mul *= 0.90
        lev_cap_mul *= 0.90
    if not final_action_allowed:
        pos_cap_mul = min(pos_cap_mul, 0.35)
        lev_cap_mul = min(lev_cap_mul, 0.50)

    return {
        "schema": "integrated_governance_risk_bridge_v1",
        "enabled": True,
        "final_regime": regime,
        "is_fallback": is_fallback,
        "final_action_allowed": final_action_allowed,
        "final_score": final_score,
        "veto_reason_codes": veto_reason_codes,
        "position_cap_multiplier": round(_clamp(pos_cap_mul, 0.20, 1.00), 4),
        "leverage_multiplier_cap": round(_clamp(lev_cap_mul, 0.30, 1.00), 4),
    }


def _derive_profile(
    risk_profile: dict[str, Any],
    now: datetime,
    source_name: str,
    mode_name: str,
    governance: dict[str, Any] | None = None,
    trinity_evolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = str(risk_profile.get("mode") or "LOCKED_MODE").upper()
    core_decision = str(risk_profile.get("core_decision") or "HOLD").upper()
    core_score = float(risk_profile.get("core_score") or 0.0)
    core_contract_version = str(risk_profile.get("core_contract_version") or "unknown")
    position_scale_cap = float(risk_profile.get("position_scale_cap") or 0.2)
    daily_loss_cap_pct = float(risk_profile.get("daily_loss_cap_pct") or 1.0)
    fused_risk_pressure = float(risk_profile.get("fused_risk_pressure") or 0.8)
    core_decision_defined = "core_decision" in risk_profile
    force_hold = core_decision_defined and core_decision == "HOLD"

    if mode == "LOCKED_MODE" or force_hold:
        out = {
            "schema_version": "risk_profile_v0.1",
            "generated_at": now.isoformat(timespec="seconds"),
            "expires_at": (now + timedelta(hours=12)).isoformat(timespec="seconds"),
            "source": source_name,
            "mode": mode_name,
            # Tight cap under LOCKED / core-HOLD: reduces fee bleed vs high-frequency scalps.
            "max_trades_per_day": 4,
            "max_position_size": 0.03,
            "maker_only_level": "strict",
            "slippage_cap_bps": 4,
            "kill_switch_threshold": 0.015,
            "trinity_governor": risk_profile,
            "singular_core": {
                "core_decision": core_decision,
                "core_score": core_score,
                "core_contract_version": core_contract_version,
            },
            "notes": "LOCKED_MODE enforced by Fact-Safe contract or singular core hold.",
        }
        if isinstance(governance, dict) and governance:
            bridge = _governance_caps(governance)
            out["governance_bridge"] = bridge
            out["max_position_size"] = round(
                _clamp(float(out["max_position_size"]) * float(bridge["position_cap_multiplier"]), 0.01, 0.20), 4
            )
            out["leverage_multiplier_cap"] = float(bridge["leverage_multiplier_cap"])
        if isinstance(trinity_evolution, dict) and trinity_evolution:
            out["trinity_evolution"] = trinity_evolution
        return out

    max_trades = int(round(_clamp(40.0 * position_scale_cap, 10.0, 80.0)))
    max_position_size = round(_clamp(0.10 * position_scale_cap, 0.03, 0.20), 4)
    # High pressure -> tighter slippage bound.
    slippage_cap_bps = int(round(_clamp(12.0 - (fused_risk_pressure * 8.0), 3.0, 15.0)))
    kill_switch = round(_clamp(daily_loss_cap_pct / 100.0, 0.015, 0.04), 4)

    out = {
        "schema_version": "risk_profile_v0.1",
        "generated_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(hours=12)).isoformat(timespec="seconds"),
        "source": source_name,
        "mode": mode_name,
        "max_trades_per_day": max_trades,
        "max_position_size": max_position_size,
        "maker_only_level": "preferred",
        "slippage_cap_bps": slippage_cap_bps,
        "kill_switch_threshold": kill_switch,
        "trinity_governor": risk_profile,
        "singular_core": {
            "core_decision": core_decision,
            "core_score": core_score,
            "core_contract_version": core_contract_version,
        },
        "notes": "ACTIVE_MODE with trinity-governed risk clamp.",
    }
    if isinstance(governance, dict) and governance:
        bridge = _governance_caps(governance)
        out["governance_bridge"] = bridge
        out["max_position_size"] = round(
            _clamp(float(out["max_position_size"]) * float(bridge["position_cap_multiplier"]), 0.01, 0.20), 4
        )
        out["leverage_multiplier_cap"] = float(bridge["leverage_multiplier_cap"])
    if isinstance(trinity_evolution, dict) and trinity_evolution:
        out["trinity_evolution"] = trinity_evolution
    return out


def _build_trinity_evolution_snapshot(
    prediction: dict[str, Any],
    daily_score: dict[str, Any],
    weights: dict[str, Any],
    prediction_btc: dict[str, Any] | None = None,
    daily_score_btc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pred_id = str(prediction.get("prediction_id") or "") if isinstance(prediction, dict) else ""
    fusion = prediction.get("fusion") if isinstance(prediction.get("fusion"), dict) else {}
    probs = prediction.get("probabilities") if isinstance(prediction.get("probabilities"), dict) else {}
    wt = weights.get("weights") if isinstance(weights.get("weights"), dict) else {}
    stats = weights.get("stats") if isinstance(weights.get("stats"), dict) else {}
    out: dict[str, Any] = {
        "schema": "trinity_evolution_snapshot_v1",
        "prediction_id": pred_id or None,
        "regime": prediction.get("regime") if isinstance(prediction, dict) else None,
        "probabilities": {
            "up": probs.get("up"),
            "flat": probs.get("flat"),
            "down": probs.get("down"),
        },
        "fusion": {
            "final_score": fusion.get("final_score"),
            "confidence": fusion.get("confidence"),
            "veto_triggered": fusion.get("veto_triggered"),
        },
        "latest_daily_score": {
            "regime_decision": daily_score.get("regime_decision") if isinstance(daily_score, dict) else None,
            "brier_score_3class": daily_score.get("brier_score_3class") if isinstance(daily_score, dict) else None,
            "realized_return_pct": daily_score.get("realized_return_pct") if isinstance(daily_score, dict) else None,
            "generated_at_utc": daily_score.get("generated_at_utc") if isinstance(daily_score, dict) else None,
        },
        "weights": {
            "mode": weights.get("mode") if isinstance(weights, dict) else None,
            "wB": wt.get("wB"),
            "wM": wt.get("wM"),
            "wS": wt.get("wS"),
            "fail_safe_triggered": stats.get("fail_safe_triggered"),
            "mean_brier_score_3class": stats.get("mean_brier_score_3class"),
            "fail_rate": stats.get("fail_rate"),
        },
    }
    if isinstance(prediction_btc, dict) and prediction_btc:
        p_btc_fusion = prediction_btc.get("fusion") if isinstance(prediction_btc.get("fusion"), dict) else {}
        p_btc_probs = (
            prediction_btc.get("probabilities")
            if isinstance(prediction_btc.get("probabilities"), dict)
            else {}
        )
        out["btc_prediction"] = {
            "prediction_id": prediction_btc.get("prediction_id"),
            "regime": prediction_btc.get("regime"),
            "probabilities": {
                "up": p_btc_probs.get("up"),
                "flat": p_btc_probs.get("flat"),
                "down": p_btc_probs.get("down"),
            },
            "fusion": {
                "final_score": p_btc_fusion.get("final_score"),
                "confidence": p_btc_fusion.get("confidence"),
                "veto_triggered": p_btc_fusion.get("veto_triggered"),
            },
        }
    if isinstance(daily_score_btc, dict) and daily_score_btc:
        out["btc_daily_score"] = {
            "regime_decision": daily_score_btc.get("regime_decision"),
            "brier_score_3class": daily_score_btc.get("brier_score_3class"),
            "realized_return_pct": daily_score_btc.get("realized_return_pct"),
            "generated_at_utc": daily_score_btc.get("generated_at_utc"),
        }
    return out


def _build_market_pulse(
    market_pulse_doc: dict[str, Any],
    *,
    breadth_override: float | None,
    foreign_net_buy_override: float | None,
    institution_net_buy_override: float | None,
    theme_score_override: float | None,
) -> dict[str, Any] | None:
    if not isinstance(market_pulse_doc, dict):
        market_pulse_doc = {}

    breadth = breadth_override
    if breadth is None:
        breadth = _optional_float(market_pulse_doc.get("advance_decline_ratio"))

    foreign_net_buy = foreign_net_buy_override
    if foreign_net_buy is None:
        foreign_net_buy = _optional_float(market_pulse_doc.get("foreign_net_buy_krw_eok"))

    institution_net_buy = institution_net_buy_override
    if institution_net_buy is None:
        institution_net_buy = _optional_float(market_pulse_doc.get("institution_net_buy_krw_eok"))

    theme_score = theme_score_override
    if theme_score is None:
        theme_score = _optional_float(market_pulse_doc.get("theme_leadership_score"))

    if None in (breadth, foreign_net_buy, institution_net_buy, theme_score):
        return None

    source = str(market_pulse_doc.get("source") or "manual_or_external").strip() or "manual_or_external"
    updated_at_utc = str(market_pulse_doc.get("updated_at_utc") or "").strip()
    if not updated_at_utc:
        updated_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return {
        "schema": "market_pulse_v1",
        "source": source,
        "updated_at_utc": updated_at_utc,
        "advance_decline_ratio": float(breadth),
        "foreign_net_buy_krw_eok": float(foreign_net_buy),
        "institution_net_buy_krw_eok": float(institution_net_buy),
        "theme_leadership_score": float(theme_score),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Fact-Safe prophecy risk profile to trader risk profile.")
    ap.add_argument("--prophecy", default=str(DEFAULT_PROPHECY))
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--source",
        default="fact_safe_prophecy.trinity_governor",
        help="risk_profile source identifier (use n8n.* convention for n8n pipelines)",
    )
    ap.add_argument("--mode", default="shadow")
    ap.add_argument(
        "--n8n-source",
        action="store_true",
        help="Shortcut for source=n8n.regime_watch.v5 and mode=n8n_shadow (legacy; prefer --repo-source for Git-SSOT sync).",
    )
    ap.add_argument(
        "--repo-source",
        action="store_true",
        help="Shortcut for source=repo.fact_safe_sync.v1 and mode=repo_shadow (scheduled Fact-Safe sync; no n8n workflow).",
    )
    ap.add_argument(
        "--allow-metadata-downgrade",
        action="store_true",
        help="Allow replacing n8n-tagged source with non-n8n metadata (intentional local/Fact-Safe override).",
    )
    ap.add_argument(
        "--integrated-governance",
        default=str(DEFAULT_GOVERNANCE),
        help="Integrated governance artifact path used for risk-cap bridge (empty string disables bridge).",
    )
    ap.add_argument(
        "--trinity-prediction",
        default=str(DEFAULT_TRINITY_PREDICTION),
        help="Trinity prediction artifact path (empty string disables evolution snapshot).",
    )
    ap.add_argument(
        "--trinity-daily-score",
        default=str(DEFAULT_TRINITY_DAILY_SCORE),
        help="Trinity daily score artifact path (optional for evolution snapshot).",
    )
    ap.add_argument(
        "--trinity-weights",
        default=str(DEFAULT_TRINITY_WEIGHTS),
        help="Trinity weights artifact path (optional for evolution snapshot).",
    )
    ap.add_argument(
        "--trinity-prediction-btc",
        default=str(DEFAULT_TRINITY_PREDICTION_BTC),
        help="Trinity BTC prediction artifact path (optional for evolution snapshot).",
    )
    ap.add_argument(
        "--trinity-daily-score-btc",
        default=str(DEFAULT_TRINITY_DAILY_SCORE_BTC),
        help="Trinity BTC daily score artifact path (optional for evolution snapshot).",
    )
    ap.add_argument(
        "--market-pulse-json",
        default="",
        help="Optional JSON path with market_pulse fields for tactical-long gate.",
    )
    ap.add_argument(
        "--market-breadth-ratio",
        type=float,
        default=None,
        help="Override: advance_decline_ratio",
    )
    ap.add_argument(
        "--market-foreign-net-buy-krw-eok",
        type=float,
        default=None,
        help="Override: foreign_net_buy_krw_eok",
    )
    ap.add_argument(
        "--market-institution-net-buy-krw-eok",
        type=float,
        default=None,
        help="Override: institution_net_buy_krw_eok",
    )
    ap.add_argument(
        "--market-theme-score",
        type=float,
        default=None,
        help="Override: theme_leadership_score",
    )
    args = ap.parse_args()

    if is_workspace_maintenance_active():
        print("SKIP: MKM_WORKSPACE_MAINTENANCE active; not writing risk profile.")
        return 0

    if args.n8n_source and args.repo_source:
        raise SystemExit("Use only one of --n8n-source or --repo-source (mutually exclusive).")

    doc = _safe_json(Path(args.prophecy))
    risk_profile = doc.get("risk_profile") if isinstance(doc.get("risk_profile"), dict) else {}
    if not risk_profile:
        raise SystemExit("Missing risk_profile in prophecy artifact.")

    now = datetime.now(timezone.utc)
    source_name = str(args.source or "fact_safe_prophecy.trinity_governor").strip()
    mode_name = str(args.mode or "shadow").strip()
    if args.n8n_source:
        source_name = "n8n.regime_watch.v5"
        mode_name = "n8n_shadow"
    elif args.repo_source:
        source_name = "repo.fact_safe_sync.v1"
        mode_name = "repo_shadow"

    out_path = Path(args.output)
    existing_out = _safe_json(out_path)
    if _would_downgrade_n8n_metadata(existing_out, source_name) and not args.allow_metadata_downgrade:
        raise SystemExit(
            "Refusing to overwrite n8n-tagged risk profile with non-n8n source/mode "
            f"(existing source={existing_out.get('source')!r}, new source={source_name!r}). "
            "Use --n8n-source or pass --source/--mode under the n8n.* namespace, "
            "use --repo-source (repo.*) with --allow-metadata-downgrade for intentional migration, "
            "or pass --allow-metadata-downgrade alone to force."
        )

    governance_doc: dict[str, Any] | None = None
    gov_arg = str(args.integrated_governance or "").strip()
    if gov_arg:
        gov_candidate = _safe_json(Path(gov_arg))
        if gov_candidate:
            governance_doc = gov_candidate

    trinity_snapshot: dict[str, Any] | None = None
    trinity_pred_arg = str(args.trinity_prediction or "").strip()
    if trinity_pred_arg:
        pred_doc = _safe_json(Path(trinity_pred_arg))
        if pred_doc:
            score_doc = _safe_json(Path(str(args.trinity_daily_score or "").strip())) if str(args.trinity_daily_score or "").strip() else {}
            weights_doc = _safe_json(Path(str(args.trinity_weights or "").strip())) if str(args.trinity_weights or "").strip() else {}
            pred_btc_doc = _safe_json(Path(str(args.trinity_prediction_btc or "").strip())) if str(args.trinity_prediction_btc or "").strip() else {}
            score_btc_doc = _safe_json(Path(str(args.trinity_daily_score_btc or "").strip())) if str(args.trinity_daily_score_btc or "").strip() else {}
            trinity_snapshot = _build_trinity_evolution_snapshot(
                prediction=pred_doc,
                daily_score=score_doc,
                weights=weights_doc,
                prediction_btc=pred_btc_doc if pred_btc_doc else None,
                daily_score_btc=score_btc_doc if score_btc_doc else None,
            )

    out_doc = _derive_profile(
        risk_profile=risk_profile,
        now=now,
        source_name=source_name,
        mode_name=mode_name,
        governance=governance_doc,
        trinity_evolution=trinity_snapshot,
    )
    market_pulse_doc: dict[str, Any] = {}
    market_pulse_arg = str(args.market_pulse_json or "").strip()
    if market_pulse_arg:
        market_pulse_doc = _safe_json(Path(market_pulse_arg))
    market_pulse = _build_market_pulse(
        market_pulse_doc,
        breadth_override=args.market_breadth_ratio,
        foreign_net_buy_override=args.market_foreign_net_buy_krw_eok,
        institution_net_buy_override=args.market_institution_net_buy_krw_eok,
        theme_score_override=args.market_theme_score,
    )
    if market_pulse is not None:
        out_doc["market_pulse"] = market_pulse
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
