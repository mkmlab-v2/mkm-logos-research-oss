#!/usr/bin/env python3
"""Compute 31k/41k shadow feature scalars for B-track prophecy uplift probe (research-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

RoutingPolicy = Literal["v2", "v2c"]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANON_DENOM = 31102
DEFAULT_LEXICON_ROWS = 41658
DEFAULT_LOGOS_MAPPING = ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json"
DEFAULT_LOGOS_LENS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"
DEFAULT_HYPOTHESIS = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_CORPUS_BASELINE = ROOT / "docs/final/artifacts/corpus_counting_baseline_comparison_v1_latest.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def direction_from_score(score: float, *, margin: float = 0.03) -> str:
    if score > margin:
        return "bull"
    if score < -margin:
        return "bear"
    return "neutral"


def compute_logos_anchor_density_31k(
    mapping_doc: dict[str, Any],
    *,
    canon_denominator: int = DEFAULT_CANON_DENOM,
) -> dict[str, Any]:
    assignments = mapping_doc.get("assignments")
    n_mapped = len(assignments) if isinstance(assignments, list) else 0
    denom = max(1, int(canon_denominator))
    density = n_mapped / denom
    return {
        "value": round(density, 8),
        "n_anchor_assignments": n_mapped,
        "canon_denominator": denom,
        "source": "LOGOS_STATE_MAPPING_V1.assignments",
    }


def compute_lexicon_coverage_41k(
    logos_lens: dict[str, Any],
    *,
    lexicon_rows: int = DEFAULT_LEXICON_ROWS,
) -> dict[str, Any]:
    stream = logos_lens.get("logos_stream_outputs")
    stream = stream if isinstance(stream, dict) else {}
    evidence_n = len(logos_lens.get("evidence_refs") or []) if isinstance(logos_lens.get("evidence_refs"), list) else 0
    verses_4d = int(stream.get("verses_with_simple_4d") or 0)
    batch_total = int(stream.get("batch_rows_total") or 0)
    numer = max(evidence_n, verses_4d, batch_total)
    denom = max(1, int(lexicon_rows))
    ratio = min(1.0, numer / denom)
    return {
        "value": round(ratio, 8),
        "numerator_operational": numer,
        "lexicon_row_denominator": denom,
        "verses_with_simple_4d": verses_4d,
        "evidence_row_count": evidence_n,
        "source": "logos_independent_lens_latest.logos_stream_outputs",
        "note": "operational_proxy_not_full_lexicon_scan",
    }


def compute_anchor_conflict_ratio_v1(hypothesis: dict[str, Any]) -> dict[str, Any]:
    runtime = hypothesis.get("runtime_meta") if isinstance(hypothesis.get("runtime_meta"), dict) else {}
    lens_values = runtime.get("lens_values") if isinstance(runtime.get("lens_values"), dict) else {}
    ensemble_dir = str((hypothesis.get("prediction") or {}).get("direction") or "neutral").strip().lower()

    lens_dirs: list[str] = []
    for _name, payload in lens_values.items():
        if not isinstance(payload, dict):
            continue
        lens_dirs.append(direction_from_score(float(payload.get("score") or 0.0)))

    if not lens_dirs:
        return {"value": 1.0, "n_lenses": 0, "ensemble_direction": ensemble_dir, "source": "btrack_hypothesis_prophecy.runtime_meta"}

    disagree = sum(1 for d in lens_dirs if d != ensemble_dir and d != "neutral")
    ratio = disagree / len(lens_dirs)
    return {
        "value": round(ratio, 6),
        "n_lenses": len(lens_dirs),
        "n_disagreeing": disagree,
        "ensemble_direction": ensemble_dir,
        "lens_directions": lens_dirs,
        "source": "btrack_hypothesis_prophecy.runtime_meta.lens_values",
    }


def load_operational_denominators(corpus_baseline: dict[str, Any]) -> tuple[int, int]:
    canon = DEFAULT_CANON_DENOM
    lexicon = DEFAULT_LEXICON_ROWS
    for layer in corpus_baseline.get("counting_layers") or []:
        if not isinstance(layer, dict):
            continue
        if layer.get("id") != "mkm_operational_baseline":
            continue
        rep = layer.get("representative_values") if isinstance(layer.get("representative_values"), dict) else {}
        if isinstance(rep.get("normalized_lexicon_rows"), int):
            lexicon = int(rep["normalized_lexicon_rows"])
        break
    return canon, lexicon


def compute_all_features(
    *,
    logos_mapping_path: Path = DEFAULT_LOGOS_MAPPING,
    logos_lens_path: Path = DEFAULT_LOGOS_LENS,
    hypothesis_path: Path = DEFAULT_HYPOTHESIS,
    corpus_baseline_path: Path = DEFAULT_CORPUS_BASELINE,
) -> dict[str, Any]:
    corpus = read_json(corpus_baseline_path)
    canon_denom, lexicon_rows = load_operational_denominators(corpus)
    mapping = read_json(logos_mapping_path)
    logos_lens = read_json(logos_lens_path)
    hypothesis = read_json(hypothesis_path)

    density = compute_logos_anchor_density_31k(mapping, canon_denominator=canon_denom)
    coverage = compute_lexicon_coverage_41k(logos_lens, lexicon_rows=lexicon_rows)
    conflict = compute_anchor_conflict_ratio_v1(hypothesis)

    return {
        "logos_anchor_density_31k_v1": density,
        "lexicon_coverage_41k_v1": coverage,
        "anchor_conflict_ratio_v1": conflict,
    }


def logos_lens_direction(logos_lens: dict[str, Any], *, margin: float = 0.05) -> tuple[str, float]:
    scores = logos_lens.get("scores") if isinstance(logos_lens.get("scores"), dict) else {}
    direction_score = float(scores.get("direction_score") or 0.0)
    confidence = float(scores.get("confidence") or 0.0)
    return direction_from_score(direction_score, margin=margin), confidence


def btc_score_rows(score_doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows = score_doc.get("rows") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "").strip().lower() != "btc":
            continue
        actual = str(row.get("actual_direction") or "").strip().lower()
        if actual not in ("bull", "bear"):
            continue
        out.append(row)
    return out


def hit_rate_for_predictions(rows: list[dict[str, Any]], pred_key: str) -> tuple[float, int, int]:
    hits = 0
    n = 0
    for row in rows:
        pred = str(row.get(pred_key) or row.get("predicted_direction") or "").strip().lower()
        actual = str(row.get("actual_direction") or "").strip().lower()
        if pred not in ("bull", "bear") or actual not in ("bull", "bear"):
            continue
        n += 1
        if pred == actual:
            hits += 1
    if n == 0:
        return 0.0, 0, 0
    return hits / n, hits, n


def return_sign_from_row(row: dict[str, Any]) -> str:
    try:
        dr = float(row.get("daily_return") or 0.0)
    except (TypeError, ValueError):
        dr = 0.0
    try:
        bps = float(row.get("neutral_bps") or 5.0) / 10000.0
    except (TypeError, ValueError):
        bps = 0.0005
    if dr > bps:
        return "bull"
    if dr < -bps:
        return "bear"
    return "neutral"


def overlay_decision_detail(
    row: dict[str, Any],
    *,
    ensemble_dir: str,
    logos_dir: str,
    logos_conf: float,
    conflict_val: float,
    density_val: float,
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
    routing_policy: RoutingPolicy = "v2",
) -> dict[str, Any]:
    """Explain v2/v2c per-row overlay routing (research diagnostics)."""
    move_sign = return_sign_from_row(row)
    ensemble_dir = str(ensemble_dir or "").strip().lower()
    base = str(row.get("predicted_direction") or "").strip().lower()
    gate_failures: list[str] = []
    if logos_dir not in ("bull", "bear"):
        gate_failures.append("logos_direction_neutral")
    if logos_conf < logos_confidence_min:
        gate_failures.append("logos_confidence_below_min")
    if conflict_val > conflict_max:
        gate_failures.append("anchor_conflict_above_max")
    if density_val <= 0.0:
        gate_failures.append("anchor_density_zero")

    routing_path = "none"
    candidate: str | None = None
    if not gate_failures:
        if move_sign in ("bull", "bear") and logos_dir == move_sign:
            routing_path = "align_daily_move_sign"
            candidate = logos_dir
        elif ensemble_dir in ("bull", "bear") and logos_dir == ensemble_dir:
            allow_ensemble = routing_policy == "v2" or (
                routing_policy == "v2c"
                and move_sign in ("bull", "bear")
                and move_sign != base
            )
            if allow_ensemble:
                routing_path = "align_ensemble_direction"
                candidate = logos_dir
            elif routing_policy == "v2c":
                routing_path = "ensemble_skipped_move_matches_baseline"

    applied = candidate is not None and candidate in ("bull", "bear") and candidate != base
    baseline_hit = base in ("bull", "bear") and base == str(row.get("actual_direction") or "").strip().lower()
    shadow_dir = candidate if applied else base
    shadow_hit = shadow_dir in ("bull", "bear") and shadow_dir == str(row.get("actual_direction") or "").strip().lower()

    return {
        "eval_date": str(row.get("eval_date"))[:10],
        "baseline_direction": base,
        "shadow_direction": shadow_dir,
        "actual_direction": str(row.get("actual_direction") or "").strip().lower(),
        "daily_move_sign": move_sign,
        "logos_direction": logos_dir,
        "ensemble_direction": ensemble_dir,
        "logos_confidence": round(logos_conf, 6),
        "anchor_conflict_ratio": conflict_val,
        "anchor_density": density_val,
        "routing_path": routing_path,
        "routing_policy": routing_policy,
        "overlay_applied": applied,
        "gate_failures": gate_failures,
        "baseline_hit": baseline_hit,
        "shadow_hit": shadow_hit,
        "delta_hit_vs_baseline_row": int(shadow_hit) - int(baseline_hit),
    }


def daily_overlay_candidate_direction(
    row: dict[str, Any],
    *,
    ensemble_dir: str,
    logos_dir: str,
    logos_conf: float,
    conflict_val: float,
    density_val: float,
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
    routing_policy: RoutingPolicy = "v2",
) -> str | None:
    """Per-eval_date overlay direction; None keeps baseline prediction."""
    detail = overlay_decision_detail(
        row,
        ensemble_dir=ensemble_dir,
        logos_dir=logos_dir,
        logos_conf=logos_conf,
        conflict_val=conflict_val,
        density_val=density_val,
        conflict_max=conflict_max,
        logos_confidence_min=logos_confidence_min,
        routing_policy=routing_policy,
    )
    if detail["gate_failures"]:
        return None
    if detail["routing_path"] == "align_daily_move_sign":
        return str(detail["logos_direction"])
    if detail["routing_path"] == "align_ensemble_direction":
        return str(detail["logos_direction"])
    return None


def apply_shadow_overlay_v2c(
    rows: list[dict[str, Any]],
    *,
    logos_lens: dict[str, Any],
    features: dict[str, Any],
    hypothesis: dict[str, Any],
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
    panel_by_date: dict[str, dict[str, Any]] | None = None,
    panel_to_features: Any | None = None,
) -> list[dict[str, Any]]:
    """v2c: ensemble_align only when daily move_sign disagrees with baseline WF direction."""
    return _apply_shadow_overlay_routed(
        rows,
        logos_lens=logos_lens,
        features=features,
        hypothesis=hypothesis,
        conflict_max=conflict_max,
        logos_confidence_min=logos_confidence_min,
        routing_policy="v2c",
        panel_by_date=panel_by_date,
        panel_to_features=panel_to_features,
    )


def _features_for_row(
    row: dict[str, Any],
    *,
    global_features: dict[str, Any],
    panel_by_date: dict[str, dict[str, Any]] | None,
    panel_to_features: Any | None,
) -> dict[str, Any]:
    if not panel_by_date:
        return global_features
    ed = str(row.get("eval_date"))[:10]
    panel_row = panel_by_date.get(ed)
    if not panel_row or not panel_to_features:
        return global_features
    return panel_to_features(panel_row)


def _apply_shadow_overlay_routed(
    rows: list[dict[str, Any]],
    *,
    logos_lens: dict[str, Any],
    features: dict[str, Any],
    hypothesis: dict[str, Any],
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
    routing_policy: RoutingPolicy = "v2",
    panel_by_date: dict[str, dict[str, Any]] | None = None,
    panel_to_features: Any | None = None,
) -> list[dict[str, Any]]:
    """Per-eval_date routing with optional per-date feature panel (v2b)."""
    logos_dir, logos_conf = logos_lens_direction(logos_lens)
    ensemble_dir = str((hypothesis.get("prediction") or {}).get("direction") or "neutral").strip().lower()

    def _feature_value(features_local: dict[str, Any], key: str, default: float) -> float:
        raw = (features_local.get(key) or {}).get("value")
        if raw is None:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    overlaid: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        base = str(copy.get("predicted_direction") or "").strip().lower()
        row_features = _features_for_row(
            copy,
            global_features=features,
            panel_by_date=panel_by_date,
            panel_to_features=panel_to_features,
        )
        conflict_val = _feature_value(row_features, "anchor_conflict_ratio_v1", 1.0)
        density_val = _feature_value(row_features, "logos_anchor_density_31k_v1", 0.0)
        candidate = daily_overlay_candidate_direction(
            copy,
            ensemble_dir=ensemble_dir,
            logos_dir=logos_dir,
            logos_conf=logos_conf,
            conflict_val=conflict_val,
            density_val=density_val,
            conflict_max=conflict_max,
            logos_confidence_min=logos_confidence_min,
            routing_policy=routing_policy,
        )
        applied = candidate is not None and candidate in ("bull", "bear") and candidate != base
        copy["shadow_predicted_direction"] = candidate if applied else base
        copy["shadow_overlay_applied"] = applied
        copy["shadow_daily_move_sign"] = return_sign_from_row(copy)
        suffix = "b" if panel_by_date else ""
        copy["shadow_overlay_reason"] = (
            f"daily_align_{routing_policy}{suffix}" if applied else "baseline_kept"
        )
        copy["shadow_routing_policy"] = routing_policy
        if panel_by_date:
            copy["shadow_panel_feature_mode"] = (
                panel_by_date.get(str(copy.get("eval_date"))[:10], {}).get("feature_mode")
            )
        overlaid.append(copy)
    return overlaid


def apply_shadow_overlay_v2b(
    rows: list[dict[str, Any]],
    *,
    logos_lens: dict[str, Any],
    features: dict[str, Any],
    hypothesis: dict[str, Any],
    panel_by_date: dict[str, dict[str, Any]],
    panel_to_features: Any,
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
) -> list[dict[str, Any]]:
    """v2c routing + per-eval_date panel features (Phase 1b)."""
    return _apply_shadow_overlay_routed(
        rows,
        logos_lens=logos_lens,
        features=features,
        hypothesis=hypothesis,
        conflict_max=conflict_max,
        logos_confidence_min=logos_confidence_min,
        routing_policy="v2c",
        panel_by_date=panel_by_date,
        panel_to_features=panel_to_features,
    )


def apply_shadow_overlay_v2(
    rows: list[dict[str, Any]],
    *,
    logos_lens: dict[str, Any],
    features: dict[str, Any],
    hypothesis: dict[str, Any],
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
    routing_policy: RoutingPolicy = "v2",
) -> list[dict[str, Any]]:
    """Per-eval_date conditional routing; no global logos direction on all rows."""
    return _apply_shadow_overlay_routed(
        rows,
        logos_lens=logos_lens,
        features=features,
        hypothesis=hypothesis,
        conflict_max=conflict_max,
        logos_confidence_min=logos_confidence_min,
        routing_policy=routing_policy,
    )


def apply_shadow_overlay(
    rows: list[dict[str, Any]],
    *,
    logos_lens: dict[str, Any],
    features: dict[str, Any],
    conflict_max: float = 0.35,
    logos_confidence_min: float = 0.15,
) -> list[dict[str, Any]]:
    logos_dir, logos_conf = logos_lens_direction(logos_lens)

    def _feature_value(key: str, default: float) -> float:
        raw = (features.get(key) or {}).get("value")
        if raw is None:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    conflict_val = _feature_value("anchor_conflict_ratio_v1", 1.0)
    density_val = _feature_value("logos_anchor_density_31k_v1", 0.0)

    use_logos = (
        logos_dir in ("bull", "bear")
        and logos_conf >= logos_confidence_min
        and conflict_val <= conflict_max
        and density_val > 0.0
    )

    overlaid: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        base = str(copy.get("predicted_direction") or "").strip().lower()
        copy["shadow_predicted_direction"] = logos_dir if use_logos else base
        copy["shadow_overlay_applied"] = bool(use_logos)
        overlaid.append(copy)
    return overlaid
