#!/usr/bin/env python3
"""Validate and aggregate personal_insight_evolution_feedback_v1 JSONL events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/personal_insight_evolution_feedback_v1.schema.json"
DEFAULT_AGG_DIR = ROOT / "reports/personal_insight_evolution"

PRODUCT_LANES = frozenset({"personadiary", "mkmlife_one_question", "clinician_cdss"})
SURFACES = frozenset(
    {
        "daily_guide",
        "monthly_guide",
        "reflect",
        "one_question_report",
        "cds_draft",
        "patient_bundle",
    }
)
PHYSICIAN_ACTIONS = frozenset({"accept", "edit", "reject", "defer"})


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_event(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if row.get("schema") != "personal_insight_evolution_feedback_v1":
        errors.append("schema_mismatch")
    lane = row.get("product_lane")
    if lane not in PRODUCT_LANES:
        errors.append("product_lane_invalid")
    surface = row.get("surface")
    if surface not in SURFACES:
        errors.append("surface_invalid")
    if not isinstance(row.get("event_id"), str) or len(row["event_id"]) < 8:
        errors.append("event_id_invalid")
    if not isinstance(row.get("ts_utc"), str):
        errors.append("ts_utc_missing")
    if not isinstance(row.get("helpful"), bool):
        errors.append("helpful_invalid")
    if row.get("hypothesis_tier") != "B":
        errors.append("hypothesis_tier_not_b")
    if row.get("non_gating") is not True:
        errors.append("non_gating_required")
    if row.get("preview_only") is not True:
        errors.append("preview_only_required")
    action = row.get("physician_action")
    if action is not None and action not in PHYSICIAN_ACTIONS:
        errors.append("physician_action_invalid")
    for key in ("clarity_score", "usefulness_score"):
        val = row.get(key)
        if val is not None and (not isinstance(val, int) or val < 1 or val > 5):
            errors.append(f"{key}_invalid")
    free_text = row.get("free_text")
    if free_text is not None and (not isinstance(free_text, str) or len(free_text) > 2000):
        errors.append("free_text_too_long")
    tags = row.get("tags")
    if tags is not None:
        if not isinstance(tags, list) or len(tags) > 12:
            errors.append("tags_invalid")
    return errors


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def default_lane_paths(base: Path | None = None) -> dict[str, Path]:
    root = base or DEFAULT_AGG_DIR
    return {
        "personadiary": root / "personadiary_v1.jsonl",
        "mkmlife_one_question": root / "mkmlife_one_question_v1.jsonl",
        "clinician_cdss": root / "clinician_v1.jsonl",
    }


def summarize_feedback(
    *,
    window_days: int = 7,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    paths = default_lane_paths(base_dir)
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    window_ms = window_days * 24 * 60 * 60 * 1000
    by_lane: dict[str, Any] = {}
    total = 0
    helpful = 0
    probe = 0
    real_user = 0

    for lane, path in paths.items():
        events = read_jsonl(path)
        recent = [
            e
            for e in events
            if isinstance(e.get("ts_utc"), str)
            and (ts := _parse_ts_ms(e["ts_utc"])) is not None
            and ts >= now_ms - window_ms
        ]
        real = [e for e in recent if not e.get("probe")]
        lane_helpful = sum(1 for e in real if e.get("helpful") is True)
        lane_total = len(real)
        physician = [e for e in real if e.get("physician_action")]
        by_lane[lane] = {
            "path": str(path),
            "total_events": len(recent),
            "real_user_events": lane_total,
            "helpful_count": lane_helpful,
            "helpful_rate": _rate(lane_helpful, lane_total),
            "physician_action_counts": _count_physician(physician),
        }
        total += len(recent)
        helpful += lane_helpful
        probe += sum(1 for e in recent if e.get("probe"))
        real_user += lane_total

    return {
        "schema": "personal_insight_evolution_feedback_summary_v1",
        "generated_at_utc": utc_now(),
        "window_days": window_days,
        "aggregate_dir": str(base_dir or DEFAULT_AGG_DIR),
        "total_events": total,
        "real_user_events": real_user,
        "probe_events": probe,
        "helpful_rate": _rate(helpful, real_user),
        "by_product_lane": by_lane,
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply_mode": "none",
        "note": "User feedback for template/tone evolution only; not clinical gating or Track A.",
    }


def _parse_ts_ms(value: str) -> float | None:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).timestamp() * 1000
    except ValueError:
        return None


def _rate(num: int, den: int) -> float:
    return round(num / den, 4) if den > 0 else 0.0


def _count_physician(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in events:
        action = e.get("physician_action")
        if isinstance(action, str):
            counts[action] = counts.get(action, 0) + 1
    return counts


def build_evolution_candidates(summary: dict[str, Any]) -> dict[str, Any]:
    """Proposal-only evolution hints from feedback aggregates (no auto-apply)."""
    candidates: list[dict[str, Any]] = []
    by_lane = summary.get("by_product_lane") or {}
    for lane, stats in by_lane.items():
        if not isinstance(stats, dict):
            continue
        rate = float(stats.get("helpful_rate") or 0)
        total = int(stats.get("real_user_events") or 0)
        if total < 3:
            continue
        if rate < 0.5:
            candidates.append(
                {
                    "candidate_id": f"piev1_{lane}_tone_refresh",
                    "product_lane": lane,
                    "kind": "template_tone_refresh",
                    "trigger": "helpful_rate_below_0_5",
                    "helpful_rate": rate,
                    "sample_size": total,
                    "mode": "proposal_only_no_auto_apply",
                }
            )
        elif rate >= 0.75:
            candidates.append(
                {
                    "candidate_id": f"piev1_{lane}_keep_template",
                    "product_lane": lane,
                    "kind": "keep_current_template",
                    "trigger": "helpful_rate_at_or_above_0_75",
                    "helpful_rate": rate,
                    "sample_size": total,
                    "mode": "proposal_only_no_auto_apply",
                }
            )
    return {
        "schema": "personal_insight_evolution_candidates_v1",
        "generated_at_utc": utc_now(),
        "mode": "proposal_only_no_auto_apply",
        "hypothesis_tier": "B",
        "research_only": True,
        "source_summary_schema": summary.get("schema"),
        "candidates": candidates,
    }


def validate_jsonl_file(path: Path) -> tuple[int, int]:
    ok = 0
    bad = 0
    for row in read_jsonl(path):
        if validate_event(row):
            bad += 1
        else:
            ok += 1
    return ok, bad
