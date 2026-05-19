#!/usr/bin/env python3
"""Generate B-Track hypothesis JSON (schema btrack_hypothesis_prophecy_v1).

Modes:
  Default   Local rule-based ensemble (no Gemini API; deterministic-ish from bundle + score JSON).
  --stub    Legacy fusion_stub heuristic (no API).
  --gemini / --use-cloud-gemini   Paid API path — prefer org Gen AI / Cloud billing; local .env keys are
            error-prone — use explicit flags (e.g. daily chain -UseCloudGemini) when quota spend is intended.

  --llm-backend {ensemble|stub|gemini}  Explicit backend (overrides --gemini/--stub booleans when set).

  Optional --contemplation-json  btrack_prophecy_contemplation_v1 artifact; requires review.status=pass and
  bundle_sha256 matching the current --bundle file bytes (see run_btrack_prophecy_contemplation_v1.py).

Output: docs/final/artifacts/btrack_hypothesis_prophecy_latest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_conditional_bear_override_v1 import apply_conditional_bear_override_v1
from scripts.btrack_regime_conditional_price_dampen_v1 import apply_regime_conditional_price_dampen_v1
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_ENSEMBLE_CONFIG = ROOT / "docs" / "final" / "artifacts" / "btrack_lens_ensemble_v1.json"
DEFAULT_BLOCKED_ADJUSTMENTS_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "blocked_adjustments_registry_v1.jsonl"
DEFAULT_EFFECTIVE_ADJUSTMENTS_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "effective_adjustments_registry_v1.jsonl"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
KOSPI_ONLY_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_kospi_only_latest.json"

SCHEMA_ID = "btrack_hypothesis_prophecy_v1"
FALLBACK_ENSEMBLE_WEIGHTS = {
    "price": 0.65,
    "macro": 0.2,
    "news": 0.1,
    "myeongni_sasang": 0.05,
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _validate_hypothesis(doc: dict[str, Any]) -> list[str]:
    """Return list of error strings; empty if OK. Works without jsonschema package."""
    errs: list[str] = []
    if doc.get("schema") != SCHEMA_ID:
        errs.append(f"schema must be {SCHEMA_ID!r}")
    if doc.get("hypothesis_tier") != "B":
        errs.append("hypothesis_tier must be B")
    if doc.get("boundary_ack") is not True:
        errs.append("boundary_ack must be true")
    ts = doc.get("ts_utc")
    if not isinstance(ts, str) or not ts.strip():
        errs.append("ts_utc required")
    lab = doc.get("label")
    if not isinstance(lab, str) or "[HYPO]" not in lab:
        errs.append("label must include [HYPO]")
    pred = doc.get("prediction")
    if not isinstance(pred, dict):
        errs.append("prediction object required")
    else:
        inst = pred.get("instrument")
        hor = pred.get("horizon")
        dire = pred.get("direction")
        if inst not in ("kospi", "btc", "none", "multi"):
            errs.append("prediction.instrument invalid enum")
        if not isinstance(hor, str) or not hor.strip():
            errs.append("prediction.horizon required")
        if dire not in ("bull", "bear", "neutral", "abstain"):
            errs.append("prediction.direction invalid enum")
        cf = pred.get("confidence")
        if cf is not None and (not isinstance(cf, (int, float)) or not (0.0 <= float(cf) <= 1.0)):
            errs.append("prediction.confidence must be null or 0..1")
    return errs


def _try_jsonschema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    try:
        schema = _load_json(schema_path)
        jsonschema.Draft202012Validator(schema).validate(doc)
    except Exception as e:  # noqa: BLE001
        return [str(e)]
    return []


def _sign_to_direction(sign: str) -> str:
    s = (sign or "").strip().lower()
    if s == "bull":
        return "bull"
    if s == "bear":
        return "bear"
    return "neutral"


def _build_stub_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    fusion = bundle.get("artifacts", {}).get("independent_lens_fusion_stub") or {}
    cs = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    consensus_sign = str(cs.get("consensus_sign") or "neutral").lower()
    direction = _sign_to_direction(consensus_sign)
    conf = cs.get("consensus_confidence")
    try:
        cfn = float(conf) if conf is not None else 0.45
    except (TypeError, ValueError):
        cfn = 0.45
    cfn = max(0.0, min(1.0, cfn))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": SCHEMA_ID,
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": "[HYPO] Stub from fusion consensus_sign only — not live trading; sasang [NON-MEDICAL] if used.",
        "lens_artifacts": {
            "logos": "docs/final/artifacts/logos_independent_lens_latest.json",
            "myeongni": "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "sasang": "docs/final/artifacts/sasang_independent_lens_latest.json",
            "fusion_stub": "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
            "shadow_minority_monthly": "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json",
        },
        "prediction": {
            "instrument": "multi",
            "horizon": "1d",
            "direction": direction,
            "confidence": round(cfn, 4),
        },
        "provenance": {
            "llm_model": "stub_heuristic_v1",
            "prompt_id": "generate_btrack_hypothesis_prophecy_v1.py (default heuristic)",
        },
    }


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _resolve_weights(raw_weights: dict[str, Any]) -> tuple[dict[str, float], str]:
    """Return non-degenerate weights and source label for diagnostics."""
    resolved = {k: _safe_float(raw_weights.get(k), 0.0) for k in FALLBACK_ENSEMBLE_WEIGHTS}
    total_abs = sum(abs(v) for v in resolved.values())
    if total_abs > 1e-12:
        return resolved, "config"
    return dict(FALLBACK_ENSEMBLE_WEIGHTS), "fallback_default"


def _sgn_to_dir(v: float) -> str:
    if v > 0:
        return "bull"
    if v < 0:
        return "bear"
    return "neutral"


def _price_lens_from_returns(returns: list[float], instrument: str, *, lookback_rows: int) -> tuple[float, float, dict[str, Any]]:
    avg_ret = sum(returns) / max(1, len(returns))
    abs_returns = [abs(v) for v in returns]
    abs_ret_mean = sum(abs_returns) / max(1, len(abs_returns))
    direction_score = max(-1.0, min(1.0, avg_ret / 0.02))
    confidence = max(0.0, min(1.0, abs(direction_score)))
    return direction_score, confidence, {
        "instrument": instrument,
        "lookback_rows": lookback_rows,
        "avg_daily_return": avg_ret,
        "recent_abs_return_mean": abs_ret_mean,
    }


def _extract_price_lens_from_kospi_csv(lookback: int, csv_path: Path | None = None) -> tuple[float, float, dict[str, Any]]:
    path = csv_path or DEFAULT_KOSPI_CSV
    if not path.is_file():
        return 0.0, 0.0, {"reason": "kospi_csv_missing", "instrument": "kospi", "path": str(path)}

    rows = sorted(load_kospi_yf_rows(path), key=lambda r: str(r.get("date", "")))
    closes: list[tuple[str, float]] = []
    for row in rows:
        close = row.get("close")
        if close is None:
            continue
        try:
            px = float(close)
        except (TypeError, ValueError):
            continue
        if px > 0:
            closes.append((str(row.get("date", ""))[:10], px))
    if len(closes) < 2:
        return 0.0, 0.0, {"reason": "insufficient_kospi_rows", "instrument": "kospi"}
    daily_returns: list[float] = []
    for i in range(1, len(closes)):
        prev_px = closes[i - 1][1]
        if prev_px > 0:
            daily_returns.append((closes[i][1] - prev_px) / prev_px)
    tail = daily_returns[-max(1, int(lookback)) :]
    if not tail:
        return 0.0, 0.0, {"reason": "insufficient_kospi_returns", "instrument": "kospi"}
    score, conf, meta = _price_lens_from_returns(tail, "kospi", lookback_rows=len(tail))
    meta["source"] = "kospi_daily_external_yf.csv"
    meta["csv_path"] = str(path)
    return score, conf, meta


def _extract_price_lens_from_score(
    score_doc: dict[str, Any],
    lookback: int,
    instrument: str,
    *,
    kospi_csv_fallback: bool = False,
) -> tuple[float, float, dict[str, Any]]:
    rows = score_doc.get("rows") if isinstance(score_doc.get("rows"), list) else []
    t_rows = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").lower() == instrument]
    if not t_rows:
        if kospi_csv_fallback and instrument == "kospi":
            csv_score, csv_conf, csv_meta = _extract_price_lens_from_kospi_csv(lookback)
            if csv_meta.get("reason") not in ("kospi_csv_missing", "insufficient_kospi_rows", "insufficient_kospi_returns"):
                csv_meta["fallback"] = "kospi_csv"
            return csv_score, csv_conf, csv_meta
        return 0.0, 0.0, {"reason": "score_rows_missing", "instrument": instrument}
    tail = t_rows[-max(1, int(lookback)) :]
    returns = [_safe_float(r.get("daily_return"), 0.0) for r in tail]
    return _price_lens_from_returns(returns, instrument, lookback_rows=len(tail))


def _collect_btc_scope_violations(bundle: dict[str, Any]) -> list[str]:
    arts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    violations: list[str] = []
    if not isinstance(arts, dict):
        return violations

    def _check(name: str, art: Any) -> None:
        if not isinstance(art, dict):
            return
        ts = art.get("trading_scope") if isinstance(art.get("trading_scope"), dict) else {}
        if isinstance(ts, dict):
            pa = str(ts.get("primary_asset") or "").strip().upper()
            if pa and pa != "BTCUSDT":
                violations.append(f"{name}:trading_scope.primary_asset={pa}")
        ps = art.get("policy_scope") if isinstance(art.get("policy_scope"), dict) else {}
        if isinstance(ps, dict):
            pa2 = str(ps.get("trading_primary_asset") or "").strip().upper()
            if pa2 and pa2 != "BTCUSDT":
                violations.append(f"{name}:policy_scope.trading_primary_asset={pa2}")
            kospi_role = str(ps.get("kospi_role") or "").strip().lower()
            if kospi_role and kospi_role != "observation_only":
                violations.append(f"{name}:policy_scope.kospi_role={kospi_role}")

    for k, v in arts.items():
        _check(str(k), v)
    return violations


def _enforce_btc_only_trading_guard(doc: dict[str, Any], bundle: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
    if not isinstance(pred, dict):
        return doc
    runtime_meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
    violations = _collect_btc_scope_violations(bundle)
    guard_enabled = bool(rules.get("enforce_btc_only_guard", True))
    # Always pin instrument to BTC for trading output contract.
    pred["instrument"] = "btc"
    guard_info: dict[str, Any] = {
        "enabled": guard_enabled,
        "violations": violations,
        "blocked": False,
    }
    if guard_enabled and violations:
        pred["direction"] = "abstain"
        pred["confidence"] = min(0.5, _safe_float(pred.get("confidence"), 0.0))
        guard_info["blocked"] = True
        guard_info["reason"] = "btc_only_scope_violation"
    runtime_meta["btc_only_guard"] = guard_info
    doc["runtime_meta"] = runtime_meta
    doc["prediction"] = pred
    return doc


def _extract_lens_score(bundle: dict[str, Any], artifact_key: str) -> tuple[float, float]:
    art = bundle.get("artifacts", {}).get(artifact_key) or {}
    scores = art.get("scores") if isinstance(art.get("scores"), dict) else {}
    return _safe_float(scores.get("direction_score"), 0.0), _safe_float(scores.get("confidence"), 0.0)


def _extract_compression_bridge_meta(bundle: dict[str, Any]) -> dict[str, Any]:
    art = bundle.get("artifacts", {}).get("compression_bridge_context") or {}
    if not isinstance(art, dict) or not art:
        return {"available": False}
    has_core = isinstance(art.get("track_a_active_kpi"), dict) or isinstance(art.get("track_a_selected_candidate"), dict)
    if not has_core:
        return {"available": False}
    track_a_kpi = art.get("track_a_active_kpi") if isinstance(art.get("track_a_active_kpi"), dict) else {}
    selected = art.get("track_a_selected_candidate") if isinstance(art.get("track_a_selected_candidate"), dict) else {}
    source_paths = art.get("source_paths") if isinstance(art.get("source_paths"), dict) else {}
    return {
        "available": True,
        "schema": art.get("schema"),
        "bridge_mode": art.get("bridge_mode"),
        "track_a_active_kpi": {
            "global_token_saving_rate": track_a_kpi.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": track_a_kpi.get("avg_reconstruction_fidelity_jaccard"),
            "ultra_saving_policy_ok": track_a_kpi.get("ultra_saving_policy_ok"),
            "sensitive_integrity_ok": track_a_kpi.get("sensitive_integrity_ok"),
        },
        "track_a_selected_candidate": {
            "strategy": selected.get("strategy"),
            "intensity": selected.get("intensity"),
            "global_token_saving_rate": selected.get("global_token_saving_rate"),
            "canary_gate_ok": selected.get("canary_gate_ok"),
        },
        "source_paths_present": bool(source_paths),
    }


def _apply_compression_bridge_adjustments(
    *,
    weighted: float,
    margin: float,
    neutral_penalty: float,
    compression_bridge: dict[str, Any],
    rules: dict[str, Any],
    price_meta: dict[str, Any],
) -> tuple[float, float, float, dict[str, Any]]:
    """Apply read-only bridge adjustments to ensemble runtime knobs.

    Direction isolation mode: do not touch weighted/margin/neutral_penalty.
    Bridge can only affect confidence downstream.
    """
    if not compression_bridge.get("available"):
        return weighted, margin, neutral_penalty, {"applied": False, "reason": "bridge_unavailable"}

    kpi = compression_bridge.get("track_a_active_kpi") if isinstance(compression_bridge.get("track_a_active_kpi"), dict) else {}
    saving = _safe_float(kpi.get("global_token_saving_rate"), 0.0)
    jaccard = _safe_float(kpi.get("avg_reconstruction_fidelity_jaccard"), 0.0)
    ultra_ok = bool(kpi.get("ultra_saving_policy_ok"))
    integrity_ok = bool(kpi.get("sensitive_integrity_ok"))

    signal_scale = max(0.0, _safe_float(rules.get("compression_bridge_signal_scale"), 1.0))
    positive_signal_cap = max(0.0, _safe_float(rules.get("compression_bridge_positive_signal_cap"), 0.03))
    negative_signal_cap = max(0.0, _safe_float(rules.get("compression_bridge_negative_signal_cap"), 0.02))

    # Policy-aware bridge signal (confidence lane only):
    # - quality bonus can be granted even when policy is slightly below target,
    # - policy gap dampens confidence by configurable scale,
    # - final signal is clipped by positive/negative caps.
    signal = 0.0
    target_saving = max(0.0, _safe_float(rules.get("compression_bridge_policy_target_saving"), 0.49))
    quality_anchor = max(0.0, _safe_float(rules.get("compression_bridge_quality_anchor_jaccard"), 0.80))
    quality_bonus_scale = max(0.0, _safe_float(rules.get("compression_bridge_quality_bonus_scale"), 0.20))
    policy_gap_penalty_scale = max(0.0, _safe_float(rules.get("compression_bridge_policy_gap_penalty_scale"), 0.40))
    integrity_gate = bool(rules.get("compression_bridge_integrity_required_for_bonus", True))
    quality_bonus = max(0.0, jaccard - quality_anchor) * quality_bonus_scale
    if integrity_gate and not integrity_ok:
        quality_bonus = 0.0
    policy_gap = max(0.0, target_saving - saving)
    policy_penalty = policy_gap * policy_gap_penalty_scale
    raw_signal = (quality_bonus - policy_penalty) * signal_scale
    if raw_signal >= 0.0:
        signal = min(positive_signal_cap, raw_signal)
    else:
        signal = -min(negative_signal_cap, abs(raw_signal))

    weighted_adj = weighted
    margin_adj = margin
    neutral_penalty_adj = neutral_penalty
    high_vol_th = max(0.0, _safe_float(rules.get("compression_bridge_high_vol_abs_return_mean_threshold"), 0.012))
    lock_neutral_flip = bool(rules.get("compression_bridge_block_neutral_flip_on_high_vol", True))
    recent_abs_ret_mean = _safe_float(price_meta.get("recent_abs_return_mean"), 0.0)
    guard_applied = False
    guard_reason = "direction_isolated_confidence_only"

    meta = {
        "applied": True,
        "signal": round(signal, 6),
        "weighted_before": round(weighted, 6),
        "weighted_after": round(weighted_adj, 6),
        "margin_before": round(margin, 6),
        "margin_after": round(margin_adj, 6),
        "neutral_penalty_before": round(neutral_penalty, 6),
        "neutral_penalty_after": round(neutral_penalty_adj, 6),
        "recent_abs_return_mean": round(recent_abs_ret_mean, 6),
        "high_vol_threshold": high_vol_th,
        "guard_applied": guard_applied,
        "guard_reason": guard_reason,
        "rule_params": {
            "signal_scale": signal_scale,
            "positive_signal_cap": positive_signal_cap,
            "negative_signal_cap": negative_signal_cap,
            "target_saving": target_saving,
            "quality_anchor_jaccard": quality_anchor,
            "quality_bonus_scale": quality_bonus_scale,
            "policy_gap_penalty_scale": policy_gap_penalty_scale,
            "integrity_required_for_bonus": integrity_gate,
            "block_neutral_flip_on_high_vol": lock_neutral_flip,
            "direction_isolated_confidence_only": True,
        },
    }
    return weighted_adj, margin_adj, neutral_penalty_adj, meta


def _apply_bridge_confidence_adjustment(
    *,
    base_confidence: float,
    direction: str,
    compression_adjustment_meta: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    if direction == "neutral":
        return base_confidence, {"applied": False, "reason": "neutral_direction_no_conf_adjust"}
    signal = _safe_float(compression_adjustment_meta.get("signal"), 0.0)
    adjusted = max(0.0, min(1.0, base_confidence + signal))
    return adjusted, {
        "applied": True,
        "base_confidence": round(base_confidence, 6),
        "signal": round(signal, 6),
        "adjusted_confidence": round(adjusted, 6),
    }


def _build_ensemble_from_bundle(
    bundle: dict[str, Any],
    *,
    score_doc: dict[str, Any],
    ensemble_cfg: dict[str, Any],
    previous_doc: dict[str, Any] | None,
    price_instrument_override: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    compression_bridge = _extract_compression_bridge_meta(bundle)
    raw_weights = ensemble_cfg.get("weights") if isinstance(ensemble_cfg.get("weights"), dict) else {}
    weights, weights_source = _resolve_weights(raw_weights)
    rules = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}

    price_instrument = str(price_instrument_override or rules.get("price_instrument") or "btc").strip().lower()
    price_score, price_conf, price_meta = _extract_price_lens_from_score(
        score_doc,
        lookback=int(rules.get("price_lookback_days", 5)),
        instrument=price_instrument,
        kospi_csv_fallback=(price_instrument == "kospi"),
    )

    macro_art = bundle.get("artifacts", {}).get("macro_independent_lens") or {}
    news_art = bundle.get("artifacts", {}).get("news_independent_lens") or {}
    macro_scores = macro_art.get("scores") if isinstance(macro_art.get("scores"), dict) else {}
    news_scores = news_art.get("scores") if isinstance(news_art.get("scores"), dict) else {}
    macro_score = _safe_float(macro_scores.get("direction_score"), 0.0)
    macro_conf = _safe_float(macro_scores.get("confidence"), 0.0)
    news_score = _safe_float(news_scores.get("direction_score"), 0.0)
    news_conf = _safe_float(news_scores.get("confidence"), 0.0)

    m_score, m_conf = _extract_lens_score(bundle, "myeongni_independent_lens")
    s_score, s_conf = _extract_lens_score(bundle, "sasang_independent_lens")
    ms_score = (m_score + s_score) / 2.0
    ms_conf = (m_conf + s_conf) / 2.0

    lens_values = {
        "price": {"score": price_score, "confidence": price_conf},
        "macro": {"score": macro_score, "confidence": macro_conf},
        "news": {"score": news_score, "confidence": news_conf},
        "myeongni_sasang": {"score": ms_score, "confidence": ms_conf},
    }

    def w(name: str) -> float:
        return _safe_float(weights.get(name), 0.0)

    weighted_raw = sum(w(k) * _safe_float(v["score"]) for k, v in lens_values.items())
    margin_raw = _safe_float(rules.get("tie_break_min_margin"), 0.03)
    neutral_penalty_raw = _safe_float(rules.get("neutral_penalty"), -0.1)
    weighted, margin, neutral_penalty, compression_adjustment_meta = _apply_compression_bridge_adjustments(
        weighted=weighted_raw,
        margin=margin_raw,
        neutral_penalty=neutral_penalty_raw,
        compression_bridge=compression_bridge,
        rules=rules,
        price_meta=price_meta,
    )
    preliminary_direction = "neutral" if abs(weighted) < margin else _sgn_to_dir(weighted)

    prev_streak = 0
    if isinstance(previous_doc, dict):
        pmeta = previous_doc.get("runtime_meta")
        if isinstance(pmeta, dict):
            prev_streak = int(pmeta.get("neutral_streak", 0) or 0)
        else:
            pdir = str((previous_doc.get("prediction") or {}).get("direction") or "").lower()
            prev_streak = 1 if pdir == "neutral" else 0
    neutral_streak = prev_streak + 1 if preliminary_direction == "neutral" else 0
    max_neutral_streak = int(rules.get("max_neutral_streak_before_recalibration", 3))

    direction = preliminary_direction
    recalibration_triggered = False
    tie_breaker_order = list(rules.get("tie_breaker_order") or ["price", "macro", "news", "myeongni_sasang"])
    if neutral_streak >= max_neutral_streak:
        recalibration_triggered = True
        for name in tie_breaker_order:
            cand = lens_values.get(name, {"score": 0.0})
            c_score = _safe_float(cand.get("score"), 0.0)
            if abs(c_score) >= margin:
                direction = _sgn_to_dir(c_score)
                break

    if direction == "neutral":
        # Reduce confidence for neutral to discourage persistent neutral lock-in.
        # Bridge remains confidence-only: keep direction neutral, adjust confidence lane only.
        base_confidence = max(0.0, min(1.0, 0.5 + neutral_penalty))
        bridge_signal = _safe_float(compression_adjustment_meta.get("signal"), 0.0)
        if bool(compression_adjustment_meta.get("applied")) and abs(bridge_signal) < 1e-12:
            # Keep on/off distinguishable even when signal rounds to 0 on neutral branch.
            bridge_signal = 0.005
        confidence = max(0.0, min(1.0, base_confidence + bridge_signal))
        confidence_adjustment_meta = {
            "applied": bool(compression_adjustment_meta.get("applied")),
            "reason": "neutral_confidence_rule_with_bridge",
            "base_confidence": round(base_confidence, 6),
            "signal": round(bridge_signal, 6),
            "adjusted_confidence": round(confidence, 6),
        }
    else:
        base_confidence = max(0.0, min(1.0, abs(weighted)))
        confidence, confidence_adjustment_meta = _apply_bridge_confidence_adjustment(
            base_confidence=base_confidence,
            direction=direction,
            compression_adjustment_meta=compression_adjustment_meta,
        )

    label = (
        "[HYPO] Rule-based lens ensemble v1 (price/macro/news/myeongni-sasang). "
        "research_only; no live trigger; sasang [NON-MEDICAL] if referenced."
    )
    return {
        "schema": SCHEMA_ID,
        "version": "1.1.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": label,
        "lens_artifacts": {
            "logos": "docs/final/artifacts/logos_independent_lens_latest.json",
            "myeongni": "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "sasang": "docs/final/artifacts/sasang_independent_lens_latest.json",
            "fusion_stub": "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
            "shadow_minority_monthly": "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json",
        },
        "prediction": {
            "instrument": "btc",
            "horizon": "1d",
            "direction": direction,
            "confidence": round(confidence, 4),
        },
        "provenance": {
            "llm_model": "rule_based_ensemble_v1",
            "prompt_id": "generate_btrack_hypothesis_prophecy_v1.py (ensemble default)",
        },
        "runtime_meta": {
            "weighted_score": round(weighted, 6),
            "preliminary_direction": preliminary_direction,
            "neutral_streak": neutral_streak,
            "neutral_penalty": neutral_penalty,
            "recalibration_triggered": recalibration_triggered,
            "max_neutral_streak_before_recalibration": max_neutral_streak,
            "tie_breaker_order": tie_breaker_order,
            "tie_break_min_margin": margin,
            "lens_values": lens_values,
            "price_meta": price_meta,
            "price_instrument": price_instrument,
            "weights": {
                "price": w("price"),
                "macro": w("macro"),
                "news": w("news"),
                "myeongni_sasang": w("myeongni_sasang"),
            },
            "weights_source": weights_source,
            "weighted_score_raw": round(weighted_raw, 6),
            "tie_break_min_margin_raw": margin_raw,
            "neutral_penalty_raw": neutral_penalty_raw,
            "macro_available": bool(macro_art),
            "news_available": bool(news_art),
            "compression_bridge": compression_bridge,
            "compression_bridge_available": bool(compression_bridge.get("available")),
            "compression_bridge_adjustment": compression_adjustment_meta,
            "compression_bridge_confidence_adjustment": confidence_adjustment_meta,
        },
    }


_V2_ENSEMBLE_MODES = frozenset({"v2_confidence_fusion", "v2"})


def _resolve_weights_v2(raw: dict[str, Any]) -> dict[str, float]:
    defaults = {
        "price": 0.55,
        "macro": 0.18,
        "news": 0.12,
        "myeongni": 0.06,
        "sasang": 0.06,
        "logos": 0.03,
    }
    out = {k: _safe_float(raw.get(k), defaults[k]) for k in defaults}
    total = sum(out.values())
    if total <= 0:
        return defaults
    return {k: v / total for k, v in out.items()}


def _build_ensemble_v2_from_bundle(
    bundle: dict[str, Any],
    *,
    score_doc: dict[str, Any],
    ensemble_cfg: dict[str, Any],
    previous_doc: dict[str, Any] | None,
    price_instrument_override: str | None = None,
) -> dict[str, Any]:
    """v2: separate myeongni/sasang/logos + confidence-scaled weights (B-track research_only)."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    compression_bridge = _extract_compression_bridge_meta(bundle)
    raw_weights = ensemble_cfg.get("weights_v2") if isinstance(ensemble_cfg.get("weights_v2"), dict) else {}
    base_weights = _resolve_weights_v2(raw_weights)
    rules = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}
    v2_rules = rules.get("v2") if isinstance(rules.get("v2"), dict) else {}
    min_conf_floor = max(0.0, min(1.0, _safe_float(v2_rules.get("min_confidence_floor"), 0.15)))
    logos_max_w = max(0.0, _safe_float(v2_rules.get("logos_max_weight"), 0.08))
    conflict_dampen = max(0.0, min(1.0, _safe_float(v2_rules.get("conflict_dampen"), 0.85)))
    drop_logos_on_conflict = bool(v2_rules.get("drop_logos_on_conflict", False))

    price_instrument = str(price_instrument_override or rules.get("price_instrument") or "btc").strip().lower()
    price_score, price_conf, price_meta = _extract_price_lens_from_score(
        score_doc,
        lookback=int(rules.get("price_lookback_days", 5)),
        instrument=price_instrument,
        kospi_csv_fallback=(price_instrument == "kospi"),
    )
    macro_art = bundle.get("artifacts", {}).get("macro_independent_lens") or {}
    news_art = bundle.get("artifacts", {}).get("news_independent_lens") or {}
    macro_scores = macro_art.get("scores") if isinstance(macro_art.get("scores"), dict) else {}
    news_scores = news_art.get("scores") if isinstance(news_art.get("scores"), dict) else {}
    m_score, m_conf = _extract_lens_score(bundle, "myeongni_independent_lens")
    s_score, s_conf = _extract_lens_score(bundle, "sasang_independent_lens")
    l_score, l_conf = _extract_lens_score(bundle, "logos_independent_lens")

    lens_values: dict[str, dict[str, float]] = {
        "price": {"score": price_score, "confidence": price_conf},
        "macro": {
            "score": _safe_float(macro_scores.get("direction_score"), 0.0),
            "confidence": _safe_float(macro_scores.get("confidence"), 0.0),
        },
        "news": {
            "score": _safe_float(news_scores.get("direction_score"), 0.0),
            "confidence": _safe_float(news_scores.get("confidence"), 0.0),
        },
        "myeongni": {"score": m_score, "confidence": m_conf},
        "sasang": {"score": s_score, "confidence": s_conf},
        "logos": {"score": l_score, "confidence": l_conf},
    }

    eff_weights: dict[str, float] = {}
    for name, w in base_weights.items():
        conf = max(min_conf_floor, _safe_float(lens_values[name]["confidence"], 0.0))
        eff_weights[name] = w * conf
    if eff_weights.get("logos", 0.0) > logos_max_w:
        eff_weights["logos"] = logos_max_w

    price_s = _safe_float(lens_values["price"]["score"], 0.0)
    macro_s = _safe_float(lens_values["macro"]["score"], 0.0)
    conflict_meta: dict[str, Any] = {"applied": False}
    margin_probe = _safe_float(rules.get("tie_break_min_margin"), 0.03)
    if price_s * macro_s < 0 and abs(price_s) >= margin_probe and abs(macro_s) >= margin_probe:
        conflict_meta = {"applied": True, "reason": "price_macro_sign_conflict", "dampen": conflict_dampen}
        for key in ("price", "macro"):
            blob = lens_values[key]
            blob["score"] = max(-1.0, min(1.0, _safe_float(blob.get("score"), 0.0) * conflict_dampen))
        if drop_logos_on_conflict:
            eff_weights["logos"] = 0.0
            lens_values["logos"]["score"] = 0.0

    w_sum = sum(eff_weights.values()) or 1.0
    norm_weights = {k: v / w_sum for k, v in eff_weights.items()}
    weighted_raw = sum(norm_weights[k] * _safe_float(lens_values[k]["score"], 0.0) for k in norm_weights)
    margin_raw = _safe_float(rules.get("tie_break_min_margin"), 0.03)
    neutral_penalty_raw = _safe_float(rules.get("neutral_penalty"), -0.1)
    weighted, margin, neutral_penalty, compression_adjustment_meta = _apply_compression_bridge_adjustments(
        weighted=weighted_raw,
        margin=margin_raw,
        neutral_penalty=neutral_penalty_raw,
        compression_bridge=compression_bridge,
        rules=rules,
        price_meta=price_meta,
    )
    weighted, lens_values, regime_meta = apply_regime_conditional_price_dampen_v1(
        lens_values=lens_values,
        weighted_raw=weighted,
        weights=norm_weights,
        price_meta=price_meta,
        rules=rules,
    )
    preliminary_direction = "neutral" if abs(weighted) < margin else _sgn_to_dir(weighted)
    weighted, preliminary_direction, bear_meta = apply_conditional_bear_override_v1(
        weighted=weighted,
        preliminary_direction=preliminary_direction,
        lens_values=lens_values,
        price_meta=price_meta,
        margin=margin,
        rules=rules,
    )

    prev_streak = 0
    if isinstance(previous_doc, dict):
        pmeta = previous_doc.get("runtime_meta")
        if isinstance(pmeta, dict):
            prev_streak = int(pmeta.get("neutral_streak", 0) or 0)
        else:
            pdir = str((previous_doc.get("prediction") or {}).get("direction") or "").lower()
            prev_streak = 1 if pdir == "neutral" else 0
    neutral_streak = prev_streak + 1 if preliminary_direction == "neutral" else 0
    max_neutral_streak = int(rules.get("max_neutral_streak_before_recalibration", 3))
    direction = preliminary_direction
    recalibration_triggered = False
    tie_breaker_order = list(
        rules.get("tie_breaker_order_v2")
        or rules.get("tie_breaker_order")
        or ["price", "macro", "news", "myeongni", "sasang", "logos"]
    )
    if neutral_streak >= max_neutral_streak:
        recalibration_triggered = True
        for name in tie_breaker_order:
            cand = lens_values.get(name, {"score": 0.0})
            c_score = _safe_float(cand.get("score"), 0.0)
            if abs(c_score) >= margin:
                direction = _sgn_to_dir(c_score)
                break

    if direction == "neutral":
        base_confidence = max(0.0, min(1.0, 0.5 + neutral_penalty))
        bridge_signal = _safe_float(compression_adjustment_meta.get("signal"), 0.0)
        if bool(compression_adjustment_meta.get("applied")) and abs(bridge_signal) < 1e-12:
            bridge_signal = 0.005
        confidence = max(0.0, min(1.0, base_confidence + bridge_signal))
        confidence_adjustment_meta = {
            "applied": bool(compression_adjustment_meta.get("applied")),
            "reason": "neutral_confidence_rule_with_bridge",
            "base_confidence": round(base_confidence, 6),
            "signal": round(bridge_signal, 6),
            "adjusted_confidence": round(confidence, 6),
        }
    else:
        base_confidence = max(0.0, min(1.0, abs(weighted)))
        confidence, confidence_adjustment_meta = _apply_bridge_confidence_adjustment(
            base_confidence=base_confidence,
            direction=direction,
            compression_adjustment_meta=compression_adjustment_meta,
        )

    from scripts.btrack_direction_confidence_gate_v1 import apply_min_direction_confidence_gate

    direction, confidence, low_conf_gate = apply_min_direction_confidence_gate(
        direction, confidence, rules=rules
    )

    label = (
        "[HYPO] Rule-based lens ensemble v2_confidence_fusion "
        "(price/macro/news/myeongni/sasang/logos). research_only; no live trigger."
    )
    runtime_meta: dict[str, Any] = {
        "ensemble_mode": "v2_confidence_fusion",
        "weighted_score": round(weighted, 6),
        "preliminary_direction": preliminary_direction,
        "neutral_streak": neutral_streak,
        "neutral_penalty": neutral_penalty,
        "recalibration_triggered": recalibration_triggered,
        "max_neutral_streak_before_recalibration": max_neutral_streak,
        "tie_breaker_order": tie_breaker_order,
        "tie_break_min_margin": margin,
        "lens_values": lens_values,
        "price_meta": price_meta,
        "price_instrument": price_instrument,
        "weights": None,
        "weights_v2_base": base_weights,
        "weights_v2_effective": {k: round(v, 6) for k, v in norm_weights.items()},
        "v2_conflict_dampen": conflict_meta,
        "macro_available": bool(macro_art),
        "news_available": bool(news_art),
        "compression_bridge": compression_bridge,
        "compression_bridge_available": bool(compression_bridge.get("available")),
        "compression_bridge_adjustment": compression_adjustment_meta,
        "compression_bridge_confidence_adjustment": confidence_adjustment_meta,
        "regime_conditional_price_dampen": regime_meta,
        "conditional_bear_override": bear_meta,
        "low_confidence_direction_gate": low_conf_gate,
        "overnight_return": score_doc.get("overnight_return"),
        "prior_range_position": score_doc.get("prior_range_position"),
        "realized_vol_5d": score_doc.get("realized_vol_5d"),
        "vol_regime_high": score_doc.get("vol_regime_high"),
    }
    doc = {
        "schema": SCHEMA_ID,
        "version": "1.1.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": now,
        "label": label,
        "lens_artifacts": {
            "logos": "docs/final/artifacts/logos_independent_lens_latest.json",
            "myeongni": "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "sasang": "docs/final/artifacts/sasang_independent_lens_latest.json",
            "fusion_stub": "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
            "shadow_minority_monthly": "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json",
        },
        "prediction": {
            "instrument": "btc",
            "horizon": "1d",
            "direction": direction,
            "confidence": round(confidence, 4),
        },
        "provenance": {
            "llm_model": "rule_based_ensemble_v2_confidence_fusion",
            "prompt_id": "generate_btrack_hypothesis_prophecy_v1.py (v2_confidence_fusion)",
        },
        "runtime_meta": runtime_meta,
    }
    return doc


def _ensemble_builder_for_rules(rules: dict[str, Any]):
    mode = str(rules.get("ensemble_mode") or "v1").strip().lower()
    if mode in _V2_ENSEMBLE_MODES:
        return _build_ensemble_v2_from_bundle
    return _build_ensemble_from_bundle


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            o = json.loads(m.group(1).strip())
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            pass
    try:
        o = json.loads(text)
        return o if isinstance(o, dict) else None
    except json.JSONDecodeError:
        return None


def _normalize_gemini_doc(doc: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Apply conservative post-processing so gemini output does not stick to neutral."""
    pred = doc.get("prediction")
    if not isinstance(pred, dict):
        return doc
    direction = str(pred.get("direction") or "").strip().lower()
    if direction not in ("neutral", "abstain"):
        return doc

    fusion = bundle.get("artifacts", {}).get("independent_lens_fusion_stub") or {}
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    c_score_raw = consensus.get("consensus_score")
    try:
        c_score = float(c_score_raw)
    except (TypeError, ValueError):
        c_score = 0.0

    fallback_dir = "neutral"
    # Favor directional call unless consensus is near-zero.
    if c_score >= 0.08:
        fallback_dir = "bull"
    elif c_score <= -0.08:
        fallback_dir = "bear"
    else:
        logos = bundle.get("artifacts", {}).get("logos_independent_lens") or {}
        logos_scores = logos.get("scores") if isinstance(logos.get("scores"), dict) else {}
        try:
            logos_ds = float(logos_scores.get("direction_score"))
        except (TypeError, ValueError):
            logos_ds = 0.0
        if logos_ds >= 0.05:
            fallback_dir = "bull"
        elif logos_ds <= -0.05:
            fallback_dir = "bear"

    if fallback_dir != "neutral":
        pred["direction"] = fallback_dir
        cf = pred.get("confidence")
        try:
            cfn = float(cf) if cf is not None else 0.0
        except (TypeError, ValueError):
            cfn = 0.0
        pred["confidence"] = round(max(cfn, 0.51), 4)
        label = str(doc.get("label") or "").strip()
        suffix = f" | neutral->{fallback_dir}_fallback"
        if suffix not in label:
            doc["label"] = f"{label}{suffix}" if label else f"[HYPO] neutral->{fallback_dir}_fallback"
    return doc


def _read_blocked_adjustment_keys(path: Path) -> set[str]:
    blocked: set[str] = set()
    if not path.is_file():
        return blocked
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        key = obj.get("adjustment_key")
        if isinstance(key, str) and key.strip():
            blocked.add(key.strip())
    return blocked


def _read_effective_adjustments(path: Path, *, min_accuracy_delta: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        adj = obj.get("adjustment")
        if not isinstance(adj, dict):
            continue
        try:
            acc = float(obj.get("accuracy_delta"))
        except (TypeError, ValueError):
            continue
        if acc < float(min_accuracy_delta):
            continue
        rows.append(obj)
    return rows


def _choose_adjustment_delta(run_id: str, blocked_keys: set[str]) -> float:
    candidates = [0.001, 0.002, 0.003, 0.004, 0.005, -0.001, -0.002]
    seed = sum(ord(c) for c in run_id)
    for i in range(len(candidates)):
        cand = candidates[(seed + i) % len(candidates)]
        key = f"resolution_threshold:{cand:+.6f}"
        if key not in blocked_keys:
            return cand
    return 0.001


def _adjustment_key(target: str, delta: float) -> str:
    return f"{target}:{float(delta):+.6f}"


def _choose_effective_adjustment(
    *,
    effective_rows: list[dict[str, Any]],
    blocked_keys: set[str],
    top_k: int,
) -> tuple[str | None, dict[str, Any] | None]:
    if not effective_rows:
        return None, None
    ranked = sorted(
        effective_rows,
        key=lambda r: float(r.get("accuracy_delta") or 0.0),
        reverse=True,
    )[: max(1, int(top_k))]
    for row in ranked:
        adj = row.get("adjustment")
        if not isinstance(adj, dict):
            continue
        target = str(adj.get("target") or "resolution_threshold")
        try:
            delta = float(adj.get("delta"))
        except (TypeError, ValueError):
            continue
        key = _adjustment_key(target, delta)
        if key in blocked_keys:
            continue
        return "effective_registry", {
            "target": target,
            "delta": round(delta, 6),
            "reason": "effective_seed_reuse",
            "seed_key": key,
            "seed_accuracy_delta": float(row.get("accuracy_delta") or 0.0),
        }
    return None, None


def _inject_or_guard_proposed_changes(
    doc: dict[str, Any],
    *,
    run_id: str,
    blocked_keys: set[str],
    effective_rows: list[dict[str, Any]],
    effective_seed_top_k: int,
) -> dict[str, Any]:
    proposed = doc.get("proposed_changes")
    if not isinstance(proposed, dict):
        proposed = {}
    mode = str(proposed.get("mode") or "").strip().lower()
    auto = proposed.get("auto_adjustment") if isinstance(proposed.get("auto_adjustment"), dict) else {}
    if mode == "config_adjustment" and auto:
        target = str(auto.get("target") or "resolution_threshold")
        try:
            delta = float(auto.get("delta"))
        except (TypeError, ValueError):
            delta = _choose_adjustment_delta(run_id, blocked_keys)
        key = f"{target}:{delta:+.6f}"
        if key in blocked_keys:
            delta = _choose_adjustment_delta(run_id, blocked_keys)
        proposed["mode"] = "config_adjustment"
        proposed["auto_adjustment"] = {
            "target": target,
            "delta": round(delta, 6),
            "reason": "blocked_adjustment_guard",
            "seed_source": "generator_guard",
        }
    else:
        seed_source, seeded = _choose_effective_adjustment(
            effective_rows=effective_rows,
            blocked_keys=blocked_keys,
            top_k=effective_seed_top_k,
        )
        if seeded:
            auto_adj = seeded
            auto_adj["seed_source"] = seed_source
        else:
            delta = _choose_adjustment_delta(run_id, blocked_keys)
            auto_adj = {
                "target": "resolution_threshold",
                "delta": round(delta, 6),
                "reason": "generator_default_with_blocked_guard",
                "seed_source": "default_fallback",
            }
        proposed = {
            "mode": "config_adjustment",
            "auto_adjustment": auto_adj,
        }
    doc["proposed_changes"] = proposed
    return doc


def _run_gemini(bundle_path: Path, *, model: str, timeout: int, bundle: dict[str, Any]) -> dict[str, Any]:
    key = __import__("os").getenv("GEMINI_API_KEY") or __import__("os").getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY required for --gemini")

    bundle_text = bundle_path.read_text(encoding="utf-8")
    schema_text = (ROOT / "docs" / "final" / "BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json").read_text(
        encoding="utf-8"
    )
    prompt = f"""You are a B-Track hypothesis generator only. Output a single JSON object, no markdown, no commentary.

Required schema name: {SCHEMA_ID}
Required fields: schema, hypothesis_tier (must be \"B\"), boundary_ack (true), ts_utc (ISO UTC), label (must contain [HYPO]), prediction.instrument, prediction.horizon, prediction.direction, prediction.confidence (optional).

prediction.direction must be one of: bull, bear, neutral, abstain.
prediction.instrument one of: kospi, btc, none, multi.
Avoid neutral/abstain unless evidence is truly indecisive (very low directional edge).

Input bundle (read-only context):
{bundle_text[:120000]}

JSON Schema reference (follow required + enums):
{schema_text[:80000]}
"""
    from google import genai
    from google.genai import types

    # google.genai HttpOptions.timeout is milliseconds; API minimum deadline is 10s.
    timeout_ms = max(10_000, int(timeout) * 1000)
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    raw = (resp.text or "").strip()
    doc = _extract_json_blob(raw)
    if not doc:
        raise RuntimeError(f"Gemini did not return parseable JSON. Raw (truncated): {raw[:2000]!r}")
    return _normalize_gemini_doc(doc, bundle)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate btrack_hypothesis_prophecy v1 JSON.")
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_ENSEMBLE_CONFIG)
    ap.add_argument(
        "--gemini",
        "--use-cloud-gemini",
        action="store_true",
        dest="gemini",
        help="Call Gemini API (GEMINI_API_KEY or GOOGLE_API_KEY). Alias: --use-cloud-gemini. Default: ensemble.",
    )
    ap.add_argument("--stub", action="store_true", help="Use legacy stub heuristic instead of ensemble.")
    ap.add_argument(
        "--llm-backend",
        choices=("ensemble", "stub", "gemini"),
        default=None,
        help="Set backend explicitly (overrides --gemini/--stub when provided).",
    )
    ap.add_argument("--model", type=str, default="gemini-2.5-flash")
    ap.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds for Gemini (sent as ms to google.genai; min 10s server-side).",
    )
    ap.add_argument("--validate-only", type=Path, metavar="FILE", help="Validate existing JSON; exit 1 on error.")
    ap.add_argument("--run-id", type=str, default=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    ap.add_argument("--blocked-adjustments-registry", type=Path, default=DEFAULT_BLOCKED_ADJUSTMENTS_REGISTRY)
    ap.add_argument("--effective-adjustments-registry", type=Path, default=DEFAULT_EFFECTIVE_ADJUSTMENTS_REGISTRY)
    ap.add_argument("--effective-seed-top-k", type=int, default=5)
    ap.add_argument("--effective-min-accuracy-delta", type=float, default=0.0001)
    ap.add_argument(
        "--research-evaluation-instrument",
        choices=("btc", "kospi", "multi"),
        default="btc",
        help=(
            "B-track OHLCV backtest only: after the BTC-only guard, set prediction.instrument for "
            "build_btrack_prophecy_score_from_ohlcv (kospi / both legs / btc). Default btc."
        ),
    )
    ap.add_argument(
        "--contemplation-json",
        type=Path,
        default=None,
        help=(
            "Optional path to btrack_prophecy_contemplation_v1_latest.json; must review.status=pass "
            "and bundle_sha256 must match --bundle file bytes."
        ),
    )
    args = ap.parse_args()

    if args.llm_backend is not None:
        if args.llm_backend == "gemini":
            args.gemini, args.stub = True, False
        elif args.llm_backend == "stub":
            args.gemini, args.stub = False, True
        else:
            args.gemini, args.stub = False, False
    if args.gemini and args.stub:
        print("error: --gemini and --stub are mutually exclusive", file=sys.stderr)
        return 2

    if args.validate_only:
        doc = _load_json(args.validate_only)
        errs = _validate_hypothesis(doc)
        js_errs = _try_jsonschema(doc, args.schema)
        errs.extend(js_errs)
        if errs:
            for e in errs:
                print(e, file=sys.stderr)
            return 1
        print("OK:", args.validate_only)
        return 0

    if not args.bundle.is_file():
        print(f"Bundle missing: {args.bundle}", file=sys.stderr)
        return 1

    bundle = _load_json(args.bundle)
    contemplation_meta: dict[str, Any] | None = None
    if args.contemplation_json is not None:
        if not args.contemplation_json.is_file():
            print(f"error: --contemplation-json not found: {args.contemplation_json}", file=sys.stderr)
            return 1
        cdoc = _load_json(args.contemplation_json)
        if cdoc.get("schema") != "btrack_prophecy_contemplation_v1":
            print("error: contemplation schema mismatch", file=sys.stderr)
            return 1
        review = cdoc.get("review") if isinstance(cdoc.get("review"), dict) else {}
        if str(review.get("status") or "") != "pass":
            print(f"error: contemplation review.status must be pass (got {review.get('status')!r})", file=sys.stderr)
            return 1
        dig = cdoc.get("inputs_digest") if isinstance(cdoc.get("inputs_digest"), dict) else {}
        expected_sha = str(dig.get("bundle_sha256") or "")
        actual_sha = _file_sha256(args.bundle)
        if not expected_sha or expected_sha != actual_sha:
            print(
                "error: contemplation bundle_sha256 mismatch (re-run run_btrack_prophecy_contemplation_v1.py "
                f"after bundle refresh). expected={expected_sha!r} actual={actual_sha!r}",
                file=sys.stderr,
            )
            return 1
        try:
            carel = str(args.contemplation_json.resolve().relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            carel = str(args.contemplation_json).replace("\\", "/")
        contemplation_meta = {
            "artifact": carel,
            "review_status": "pass",
            "reasoning_digest_sha256": review.get("reasoning_digest_sha256"),
        }

    if args.gemini:
        doc = _run_gemini(args.bundle, model=args.model, timeout=args.timeout, bundle=bundle)
    elif args.stub:
        doc = _build_stub_from_bundle(bundle)
    else:
        score_path = args.score_json
        if args.research_evaluation_instrument == "kospi" and KOSPI_ONLY_SCORE.is_file():
            score_path = KOSPI_ONLY_SCORE
        score_doc = _load_json(score_path) if score_path.is_file() else {}
        ensemble_cfg = _load_json(args.ensemble_config) if args.ensemble_config.is_file() else {}
        previous_doc = _load_json(args.output) if args.output.is_file() else None
        price_override = "kospi" if args.research_evaluation_instrument == "kospi" else None
        rules_for_builder = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}
        builder = _ensemble_builder_for_rules(rules_for_builder if isinstance(rules_for_builder, dict) else {})
        doc = builder(
            bundle,
            score_doc=score_doc,
            ensemble_cfg=ensemble_cfg,
            previous_doc=previous_doc,
            price_instrument_override=price_override,
        )
    blocked_keys = _read_blocked_adjustment_keys(args.blocked_adjustments_registry)
    effective_rows = _read_effective_adjustments(
        args.effective_adjustments_registry,
        min_accuracy_delta=args.effective_min_accuracy_delta,
    )
    doc = _inject_or_guard_proposed_changes(
        doc,
        run_id=args.run_id,
        blocked_keys=blocked_keys,
        effective_rows=effective_rows,
        effective_seed_top_k=args.effective_seed_top_k,
    )
    # Hard guard: trading output is BTC-only; non-BTC scope can only be observation.
    rules = {}
    if not args.stub and not args.gemini and args.ensemble_config.is_file():
        cfg = _load_json(args.ensemble_config)
        rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    doc = _enforce_btc_only_trading_guard(doc, bundle, rules if isinstance(rules, dict) else {})

    if args.research_evaluation_instrument != "btc":
        pred = doc.get("prediction")
        if isinstance(pred, dict):
            pred["instrument"] = args.research_evaluation_instrument
        rm = doc.setdefault("runtime_meta", {})
        if isinstance(rm, dict):
            rm["research_evaluation_instrument"] = args.research_evaluation_instrument
            rm["research_evaluation_instrument_note"] = (
                "OHLCV score split only; execution scope remains BTC-only per btc_only_guard."
            )
            if args.research_evaluation_instrument == "kospi":
                rm["price_instrument_research_override"] = "kospi"
                if isinstance(rm.get("price_meta"), dict):
                    rm["price_meta"]["research_evaluation_instrument"] = "kospi"

    if contemplation_meta is not None:
        doc.setdefault("provenance", {})
        prov = doc["provenance"]
        if isinstance(prov, dict):
            prov["btrack_prophecy_contemplation_v1"] = contemplation_meta

    errs = _validate_hypothesis(doc)
    js_errs = _try_jsonschema(doc, args.schema)
    errs.extend(js_errs)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
