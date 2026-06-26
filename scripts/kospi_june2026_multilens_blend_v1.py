#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June 2026 KOSPI multilens v2 blend helpers [HYPO][research_only]."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ART = ROOT / "docs/final/artifacts"
BUNDLE = ART / "btrack_llm_input_bundle_latest.json"
ENSEMBLE_CFG = ART / "btrack_lens_ensemble_v1.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dir_from_score(score: float, *, threshold: float = 0.08) -> str:
    if score > threshold:
        return "bull"
    if score < -threshold:
        return "bear"
    return "neutral"


def _lens_direction_from_artifact(path: Path) -> tuple[str, float, bool]:
    doc = _read_json(path)
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    try:
        ds = float(scores.get("direction_score") or 0.0)
    except (TypeError, ValueError):
        ds = 0.0
    return _dir_from_score(ds), ds, bool(doc)


def load_static_lenses(
    *,
    myeongni_path: Path | None = None,
    sasang_path: Path | None = None,
) -> dict[str, Any]:
    logos_p = ART / "logos_independent_lens_latest.json"
    myeongni_p = myeongni_path or (ART / "myeongni_independent_lens_latest.json")
    sasang_p = sasang_path or (ART / "sasang_independent_lens_latest.json")
    macro_p = ART / "macro_independent_lens_latest.json"

    logos_d, logos_s, logos_ok = _lens_direction_from_artifact(logos_p)
    myeongni_d, myeongni_s, myeongni_ok = _lens_direction_from_artifact(myeongni_p)
    sasang_d, sasang_s, sasang_ok = _lens_direction_from_artifact(sasang_p)
    macro_d, macro_s, macro_ok = _lens_direction_from_artifact(macro_p)

    field = _read_json(ART / "global_market_overnight_signals_v1_latest.json")
    tilt = str(field.get("composite_tilt") or "neutral")
    if tilt in ("risk_off_overnight", "risk_off"):
        field_dir = "bear"
    elif tilt in ("risk_on_overnight", "risk_on"):
        field_dir = "bull"
    else:
        field_dir = "neutral"

    return {
        "logos": {"direction": logos_d, "score": logos_s, "loaded": logos_ok, "non_gating": True, "path": str(logos_p)},
        "myeongni_independent": {
            "direction": myeongni_d,
            "score": myeongni_s,
            "loaded": myeongni_ok,
            "path": str(myeongni_p),
        },
        "sasang": {"direction": sasang_d, "score": sasang_s, "loaded": sasang_ok, "path": str(sasang_p)},
        "macro": {"direction": macro_d, "score": macro_s, "loaded": macro_ok, "path": str(macro_p)},
        "field_regime": {
            "direction": field_dir,
            "composite_tilt": tilt,
            "loaded": bool(field),
            "path": str(ART / "global_market_overnight_signals_v1_latest.json"),
        },
    }


def load_ensemble_kospi_per_date(eval_dates: list[str]) -> dict[str, dict[str, Any]]:
    """Causal KOSPI v2 ensemble per eval_date (B-track bundle snapshot)."""
    if not BUNDLE.is_file() or not eval_dates:
        return {}
    try:
        from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows
    except ImportError:
        return {}

    bundle = _read_json(BUNDLE)
    cfg = deepcopy(_read_json(ENSEMBLE_CFG))
    rules = dict(cfg.get("rules") or {})
    rules["ensemble_mode"] = "v2_confidence_fusion"
    rules["price_instrument"] = "kospi"
    rules["enforce_btc_only_guard"] = False
    cfg["rules"] = rules

    rows = compute_per_date_direction_rows(
        bundle=bundle,
        ensemble_cfg=cfg,
        eval_dates=eval_dates,
        btc_csv=KOSPI_CSV,
        instrument="kospi",
    )
    return {str(r.get("eval_date")): r for r in rows if r.get("eval_date")}


def default_weights_v2() -> dict[str, float]:
    return {
        "session_myeongni": 0.22,
        "myeongni_independent": 0.14,
        "sasang": 0.12,
        "logos_non_gating": 0.08,
        "macro": 0.10,
        "field_regime": 0.12,
        "momentum_overlay": 0.12,
        "ensemble_kospi_causal": 0.10,
    }


def _resolve_winner(
    votes: dict[str, float],
    *,
    total_w: float,
    policy: dict[str, Any],
) -> tuple[str, str]:
    """Return (winner, resolution_mode)."""
    bull = float(votes.get("bull", 0.0))
    bear = float(votes.get("bear", 0.0))
    neutral = float(votes.get("neutral", 0.0))
    min_w = float(policy.get("directional_winner_min_weight", 0.28))
    margin = float(policy.get("directional_margin_ratio", 1.12))
    prefer_dir = bool(policy.get("prefer_directional_over_neutral", True))
    require_plurality = bool(policy.get("require_directional_plurality", True))

    winner = max(votes, key=lambda k: votes[k])
    if winner == "neutral":
        return "neutral", "neutral_plurality"

    if prefer_dir:
        if (
            bear >= min_w
            and bear >= bull * margin
            and (not require_plurality or bear > neutral)
        ):
            return "bear", "directional_bear"
        if (
            bull >= min_w
            and bull >= bear * margin
            and (not require_plurality or bull > neutral)
        ):
            return "bull", "directional_bull"

    if votes[winner] / max(total_w, 1e-9) < 0.34:
        return "neutral", "plurality_low"
    return winner, "plurality"


def blend_v2_multilens(
    *,
    session_map: str,
    session_score: float,
    momentum_dir: str,
    static_lenses: dict[str, Any],
    ensemble_row: dict[str, Any] | None,
    weights: dict[str, float],
    neutral_band: float,
    blend_policy: dict[str, Any] | None = None,
) -> tuple[str, float, dict[str, Any]]:
    votes = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
    w = {**default_weights_v2(), **weights}

    channels: list[tuple[str, str, float, dict[str, Any]]] = []
    sess_dir = "neutral" if session_map == "sideways" else session_map
    channels.append(("session_myeongni", sess_dir, float(w.get("session_myeongni", 0)), {"score": session_score}))

    for key, wkey in (
        ("myeongni_independent", "myeongni_independent"),
        ("sasang", "sasang"),
        ("macro", "macro"),
    ):
        lens = static_lenses.get(key) or {}
        if lens.get("loaded"):
            channels.append((key, str(lens.get("direction") or "neutral"), float(w.get(wkey, 0)), lens))

    logos = static_lenses.get("logos") or {}
    if logos.get("loaded"):
        channels.append(
            ("logos_non_gating", str(logos.get("direction") or "neutral"), float(w.get("logos_non_gating", 0)), logos)
        )

    field = static_lenses.get("field_regime") or {}
    if field.get("loaded"):
        channels.append(
            ("field_regime", str(field.get("direction") or "neutral"), float(w.get("field_regime", 0)), field)
        )

    channels.append(("momentum_overlay", momentum_dir, float(w.get("momentum_overlay", 0)), {}))

    if ensemble_row:
        ens_dir = str(ensemble_row.get("predicted_direction") or "neutral")
        channels.append(
            (
                "ensemble_kospi_causal",
                ens_dir,
                float(w.get("ensemble_kospi_causal", 0)),
                {
                    "ensemble_mode": ensemble_row.get("ensemble_mode"),
                    "weighted_score": ensemble_row.get("weighted_score"),
                    "lens_values": ensemble_row.get("lens_values"),
                },
            )
        )

    contrib: list[dict[str, Any]] = []
    for name, direction, weight, meta in channels:
        if direction not in votes:
            direction = "neutral"
        votes[direction] = votes.get(direction, 0.0) + weight
        contrib.append({"channel": name, "direction": direction, "weight": round(weight, 4), "meta": meta})

    total_w = sum(c[2] for c in channels) or 1.0
    policy = blend_policy if isinstance(blend_policy, dict) else {}
    winner, resolution_mode = _resolve_winner(votes, total_w=total_w, policy=policy)

    blended_score = 0.0
    for name, direction, weight, meta in channels:
        if name == "session_myeongni":
            blended_score += weight * session_score
        elif direction == "bull":
            blended_score += weight * 0.12
        elif direction == "bear":
            blended_score -= weight * 0.12
        if name == "ensemble_kospi_causal" and meta.get("weighted_score") is not None:
            try:
                blended_score += weight * float(meta["weighted_score"])
            except (TypeError, ValueError):
                pass

    blended_score = max(-1.0, min(1.0, blended_score))
    if abs(blended_score) <= neutral_band * 0.5 and winner in ("bull", "bear"):
        if votes.get("neutral", 0) >= votes.get(winner, 0) * 0.85:
            winner = "neutral"
            resolution_mode = "neutral_plurality"

    detail = {
        "profile": "v2_multilens",
        "weights": {k: round(float(v), 4) for k, v in w.items()},
        "votes": {k: round(v, 4) for k, v in votes.items()},
        "winner_resolution": resolution_mode,
        "channels": contrib,
        "blended_score": round(blended_score, 6),
        "four_ai_contract": "4AI_core + Absolute_Balance_Coordinator_Mode (blend state; not 5th lens)",
    }
    return winner, round(blended_score, 6), detail


def integration_maturity_rubric(static_lenses: dict[str, Any], ensemble_dates: int, n_days: int) -> dict[str, Any]:
    scores = {
        "logos": 4.0 if static_lenses.get("logos", {}).get("loaded") else 0.0,
        "myeongni_independent": 4.0 if static_lenses.get("myeongni_independent", {}).get("loaded") else 0.0,
        "sasang": 4.0 if static_lenses.get("sasang", {}).get("loaded") else 0.0,
        "macro": 3.5 if static_lenses.get("macro", {}).get("loaded") else 0.0,
        "field_regime": 4.0 if static_lenses.get("field_regime", {}).get("loaded") else 0.0,
        "session_myeongni_per_date": 4.5,
        "ensemble_kospi_causal": min(5.0, 5.0 * ensemble_dates / max(1, n_days)),
    }
    avg = sum(scores.values()) / len(scores)
    return {
        "rubric_max": 5.0,
        "channel_scores": scores,
        "integration_avg_0_5": round(avg, 2),
        "integration_pct": round(avg / 5.0 * 100.0, 1),
        "hypothesis_tier": "B",
        "note": "Rubric for multilens wiring depth; not price hit-rate.",
    }
