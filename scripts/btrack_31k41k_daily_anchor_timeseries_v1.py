#!/usr/bin/env python3
"""Per-eval_date 31k/41k anchor metrics from verse_4pipeline + score rows (research-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

PanelMergePolicy = Literal["max_per_row_global", "per_row_strict"]

DEFAULT_CANON_DENOM = 31102
DEFAULT_LEXICON_ROWS = 41658


def read_json(path: Path) -> dict[str, Any] | list[Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def direction_from_score(score: float, *, margin: float = 0.05) -> str:
    if score > margin:
        return "bull"
    if score < -margin:
        return "bear"
    return "neutral"


def verse_direction_from_4d(v4: dict[str, float], *, margin: float = 0.05) -> str:
    score = float(v4.get("S", 0.0)) - float(v4.get("M", 0.0))
    return direction_from_score(score, margin=margin)


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


def load_verse_subset(path: Path, verse_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Load pipeline vectors + gematria for a small verse_id set from full canon JSON."""
    if not verse_ids:
        return {}
    want = {str(v).strip() for v in verse_ids}
    raw = read_json(path)
    if not isinstance(raw, list):
        return {}
    found: dict[str, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "").strip()
        if vid not in want:
            continue
        p4 = row.get("pipeline4_unified_v2") if isinstance(row.get("pipeline4_unified_v2"), dict) else {}
        v4 = p4.get("vector_4d") if isinstance(p4.get("vector_4d"), dict) else {}
        p2 = row.get("pipeline2_gematria_general") if isinstance(row.get("pipeline2_gematria_general"), dict) else {}
        norm = float(p2.get("normalized_value") or 0.0)
        if not v4:
            continue
        found[vid] = {
            "vector_4d": {k: float(v4[k]) for k in ("S", "L", "K", "M") if k in v4},
            "gematria_normalized": norm,
        }
        if len(found) >= len(want):
            break
    return found


def load_verse_id_catalog(path: Path) -> list[str]:
    """Ordered canon verse_id list (one JSON parse; research batch only)."""
    raw = read_json(path)
    if not isinstance(raw, list):
        return []
    catalog: list[str] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "").strip()
        if vid:
            catalog.append(vid)
    return catalog


def rotating_sample_indices(
    eval_date: str,
    date_ordinal: int,
    n_verses: int,
    sample_size: int,
) -> list[int]:
    """Deterministic per-date rotating window into canon index space."""
    if n_verses <= 0 or sample_size <= 0:
        return []
    seed = hash(eval_date) & 0x7FFFFFFF
    size = min(int(sample_size), n_verses)
    return [(date_ordinal * 997 + k * 1009 + seed) % n_verses for k in range(size)]


def rotating_sample_verse_ids(
    eval_date: str,
    date_ordinal: int,
    catalog: list[str],
    sample_size: int,
) -> list[str]:
    n = len(catalog)
    if n == 0:
        return []
    return [catalog[i] for i in rotating_sample_indices(eval_date, date_ordinal, n, sample_size)]


def union_rotating_sample_ids(
    dates: list[str],
    catalog: list[str],
    sample_size: int,
) -> set[str]:
    want: set[str] = set()
    for i, d in enumerate(dates):
        for vid in rotating_sample_verse_ids(d, i, catalog, sample_size):
            want.add(vid)
    return want


def assignment_verse_ids(mapping_doc: dict[str, Any]) -> list[str]:
    assignments = mapping_doc.get("assignments")
    if not isinstance(assignments, list):
        return []
    out: list[str] = []
    for item in assignments:
        if isinstance(item, dict) and item.get("verse_id"):
            out.append(str(item["verse_id"]).strip())
    return out


def compute_timeseries_row(
    btc_row: dict[str, Any],
    *,
    verse_by_id: dict[str, dict[str, Any]],
    assignment_ids: list[str],
    canon_denominator: int = DEFAULT_CANON_DENOM,
    lexicon_rows: int = DEFAULT_LEXICON_ROWS,
) -> dict[str, Any]:
    """Per-date 31k/41k scalars from anchor verses aligned with that day's move sign."""
    move_sign = return_sign_from_row(btc_row)
    pred = str(btc_row.get("predicted_direction") or "").strip().lower()

    n_assigned = 0
    n_aligned_move = 0
    n_gematria_aligned = 0
    votes: dict[str, int] = {"bull": 0, "bear": 0}

    for vid in assignment_ids:
        payload = verse_by_id.get(vid)
        if not payload:
            continue
        v4 = payload.get("vector_4d") if isinstance(payload.get("vector_4d"), dict) else {}
        if not v4:
            continue
        n_assigned += 1
        vd = verse_direction_from_4d(v4)
        if vd in votes:
            votes[vd] += 1
        if move_sign in ("bull", "bear") and vd == move_sign:
            n_aligned_move += 1
        norm = float(payload.get("gematria_normalized") or 0.0)
        gem_dir = direction_from_score(norm - 0.5, margin=0.02)
        if move_sign in ("bull", "bear") and gem_dir == move_sign:
            n_gematria_aligned += 1

    denom = max(1, int(canon_denominator))
    lex_denom = max(1, int(lexicon_rows))
    density_val = round(n_aligned_move / denom, 8)
    coverage_val = round(min(1.0, n_gematria_aligned / lex_denom), 8)

    if votes["bull"] > votes["bear"]:
        panel_logos_dir = "bull"
    elif votes["bear"] > votes["bull"]:
        panel_logos_dir = "bear"
    else:
        panel_logos_dir = "neutral"

    if pred in ("bull", "bear") and panel_logos_dir in ("bull", "bear"):
        conflict_val = 0.0 if pred == panel_logos_dir else 1.0
    else:
        conflict_val = 0.5

    return {
        "eval_date": str(btc_row.get("eval_date"))[:10],
        "daily_move_sign": move_sign,
        "panel_logos_direction": panel_logos_dir,
        "n_anchor_verses_resolved": n_assigned,
        "n_anchor_aligned_with_move": n_aligned_move,
        "logos_anchor_density_31k_v1": {
            "value": density_val,
            "n_anchor_aligned_with_move": n_aligned_move,
            "canon_denominator": denom,
            "source": "verse_4pipeline.assignments_x_daily_move_sign",
        },
        "lexicon_coverage_41k_v1": {
            "value": coverage_val,
            "n_gematria_aligned_proxy": n_gematria_aligned,
            "lexicon_row_denominator": lex_denom,
            "source": "verse_4pipeline.gematria_normalized_x_daily_move_sign",
            "note": "assignment_subset_proxy_not_full_lexicon_scan",
        },
        "anchor_conflict_ratio_v1": {
            "value": round(conflict_val, 6),
            "panel_logos_direction": panel_logos_dir,
            "predicted_direction": pred,
            "source": "panel_logos_vs_baseline_prediction",
        },
        "feature_mode": "timeseries_v1",
        "timeseries_ready": True,
    }


def _alignment_counts(
    verse_ids: list[str],
    verse_by_id: dict[str, dict[str, Any]],
    move_sign: str,
) -> tuple[int, int, int, dict[str, int]]:
    """resolved, move-aligned 4d, gematria-aligned, direction votes."""
    n_resolved = 0
    n_aligned_move = 0
    n_gematria_aligned = 0
    votes: dict[str, int] = {"bull": 0, "bear": 0}
    seen: set[str] = set()
    for vid in verse_ids:
        if vid in seen:
            continue
        seen.add(vid)
        payload = verse_by_id.get(vid)
        if not payload:
            continue
        v4 = payload.get("vector_4d") if isinstance(payload.get("vector_4d"), dict) else {}
        if not v4:
            continue
        n_resolved += 1
        vd = verse_direction_from_4d(v4)
        if vd in votes:
            votes[vd] += 1
        if move_sign in ("bull", "bear") and vd == move_sign:
            n_aligned_move += 1
        norm = float(payload.get("gematria_normalized") or 0.0)
        gem_dir = direction_from_score(norm - 0.5, margin=0.02)
        if move_sign in ("bull", "bear") and gem_dir == move_sign:
            n_gematria_aligned += 1
    return n_resolved, n_aligned_move, n_gematria_aligned, votes


def compute_timeseries_row_v2(
    btc_row: dict[str, Any],
    *,
    verse_by_id: dict[str, dict[str, Any]],
    assignment_ids: list[str],
    rotating_ids: list[str],
    rolling_sample_size: int,
    canon_denominator: int = DEFAULT_CANON_DENOM,
    lexicon_rows: int = DEFAULT_LEXICON_ROWS,
) -> dict[str, Any]:
    """timeseries_v2: assignments + per-date rotating lexicon sample (research-only)."""
    move_sign = return_sign_from_row(btc_row)
    pred = str(btc_row.get("predicted_direction") or "").strip().lower()
    combined = list(dict.fromkeys(list(assignment_ids) + list(rotating_ids)))

    n_resolved, n_aligned_move, n_gematria_aligned, votes = _alignment_counts(
        combined, verse_by_id, move_sign
    )
    n_rotating_resolved = sum(1 for vid in rotating_ids if vid in verse_by_id)

    denom = max(1, int(canon_denominator))
    lex_denom = max(1, int(lexicon_rows))
    density_val = round(n_aligned_move / denom, 8)
    coverage_val = round(min(1.0, n_gematria_aligned / lex_denom), 8)

    if votes["bull"] > votes["bear"]:
        panel_logos_dir = "bull"
    elif votes["bear"] > votes["bull"]:
        panel_logos_dir = "bear"
    else:
        panel_logos_dir = "neutral"

    if pred in ("bull", "bear") and panel_logos_dir in ("bull", "bear"):
        conflict_val = 0.0 if pred == panel_logos_dir else 1.0
    else:
        conflict_val = 0.5

    return {
        "eval_date": str(btc_row.get("eval_date"))[:10],
        "daily_move_sign": move_sign,
        "panel_logos_direction": panel_logos_dir,
        "n_anchor_verses_resolved": n_resolved,
        "n_anchor_aligned_with_move": n_aligned_move,
        "n_rotating_sample_resolved": n_rotating_resolved,
        "rolling_lexicon_sample_size": int(rolling_sample_size),
        "logos_anchor_density_31k_v1": {
            "value": density_val,
            "n_anchor_aligned_with_move": n_aligned_move,
            "n_verses_in_union": len(combined),
            "canon_denominator": denom,
            "source": "verse_4pipeline.assignments_plus_rotating_sample_x_daily_move_sign",
        },
        "lexicon_coverage_41k_v1": {
            "value": coverage_val,
            "n_gematria_aligned_proxy": n_gematria_aligned,
            "lexicon_row_denominator": lex_denom,
            "source": "rotating_lexicon_sample_v1",
            "note": "rotating_sample_not_full_lexicon_scan",
        },
        "anchor_conflict_ratio_v1": {
            "value": round(conflict_val, 6),
            "panel_logos_direction": panel_logos_dir,
            "predicted_direction": pred,
            "source": "panel_logos_vs_baseline_prediction",
        },
        "feature_mode": "timeseries_v2",
        "timeseries_ready": True,
    }


def panel_row_to_feature_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Shape expected by shadow overlay (_feature_value reads .value)."""
    return {
        "logos_anchor_density_31k_v1": row.get("logos_anchor_density_31k_v1") or {"value": 0.0},
        "lexicon_coverage_41k_v1": row.get("lexicon_coverage_41k_v1") or {"value": 0.0},
        "anchor_conflict_ratio_v1": row.get("anchor_conflict_ratio_v1") or {"value": 1.0},
    }


def panel_row_to_overlay_features(
    panel_row: dict[str, Any],
    global_features: dict[str, Any],
    *,
    merge_policy: PanelMergePolicy = "max_per_row_global",
) -> dict[str, Any]:
    """v2b overlay gates: per-date density/coverage; conflict stays global (lens ensemble)."""
    local = panel_row_to_feature_dict(panel_row)

    def _val(key: str) -> float:
        raw = (local.get(key) or {}).get("value")
        try:
            return float(raw if raw is not None else 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _gval(key: str) -> float:
        raw = (global_features.get(key) or {}).get("value")
        try:
            return float(raw if raw is not None else 0.0)
        except (TypeError, ValueError):
            return 0.0

    if merge_policy == "per_row_strict":
        density = _val("logos_anchor_density_31k_v1")
        coverage = _val("lexicon_coverage_41k_v1")
    else:
        density = max(_val("logos_anchor_density_31k_v1"), _gval("logos_anchor_density_31k_v1"))
        coverage = max(_val("lexicon_coverage_41k_v1"), _gval("lexicon_coverage_41k_v1"))

    merged = {
        "logos_anchor_density_31k_v1": {
            **(local.get("logos_anchor_density_31k_v1") or {}),
            "value": round(density, 8),
            "merge_policy": merge_policy,
        },
        "lexicon_coverage_41k_v1": {
            **(local.get("lexicon_coverage_41k_v1") or {}),
            "value": round(coverage, 8),
            "merge_policy": merge_policy,
        },
        "anchor_conflict_ratio_v1": global_features.get("anchor_conflict_ratio_v1")
        or local.get("anchor_conflict_ratio_v1")
        or {"value": 1.0},
    }
    return merged
