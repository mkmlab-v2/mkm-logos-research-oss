#!/usr/bin/env python3
"""SSOT loader for evolution auto-apply allowlist (B-track / commander / general holdout)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = ROOT / "docs" / "final" / "artifacts" / "evolution_auto_apply_allowlist_v1_latest.json"


def load_allowlist(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_ALLOWLIST
    if not p.is_file():
        raise FileNotFoundError(f"Missing allowlist: {p}")
    doc = json.loads(p.read_text(encoding="utf-8-sig"))
    if str(doc.get("schema") or "") != "evolution_auto_apply_allowlist_v1":
        raise ValueError(f"Invalid allowlist schema: {doc.get('schema')}")
    return doc


def allowed_btrack_parameter_targets(path: Path | None = None) -> frozenset[str]:
    doc = load_allowlist(path)
    rails = doc.get("rails") if isinstance(doc.get("rails"), dict) else {}
    btrack = rails.get("btrack_price") if isinstance(rails.get("btrack_price"), dict) else {}
    raw = btrack.get("allowed_parameter_targets")
    if not isinstance(raw, list):
        return frozenset()
    return frozenset(str(x) for x in raw if x)


def assert_btrack_parameter_target_allowed(target: str, *, path: Path | None = None) -> None:
    allowed = allowed_btrack_parameter_targets(path)
    if target not in allowed:
        raise ValueError(
            f"B-track parameter target {target!r} not in evolution_auto_apply_allowlist "
            f"(allowed={sorted(allowed)})"
        )


def assert_headline_gate_sweep_allowed(
    *,
    min_confidence: float,
    score_abs_deadzone: float,
    path: Path | None = None,
) -> None:
    """Sweep grids must only use allowlisted headline gate parameter names."""
    assert_btrack_parameter_target_allowed("min_confidence_active_gate", path=path)
    assert_btrack_parameter_target_allowed("score_abs_deadzone", path=path)
    for label, value in (
        ("min_confidence_active_gate", min_confidence),
        ("score_abs_deadzone", score_abs_deadzone),
    ):
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{label} out of range [0,1]: {value}")


def assert_headline_kpi_promotion_allowed(
    *,
    min_confidence: float,
    score_abs_deadzone: float,
    output: Path,
    path: Path | None = None,
) -> None:
    """Human script ``promote_op28_headline_kpi_v1`` only — gate params + headline SSOT path."""
    doc = load_allowlist(path)
    signoff = doc.get("human_signoff_required_for")
    if not isinstance(signoff, list) or "promote_op28_headline_kpi_v1" not in signoff:
        raise ValueError(
            "allowlist must list promote_op28_headline_kpi_v1 under human_signoff_required_for"
        )
    forbidden = doc.get("forbidden_targets")
    if isinstance(forbidden, list) and "headline_kpi_overwrite_without_human_script" in forbidden:
        pass  # this script is the designated human writer
    assert_headline_gate_sweep_allowed(
        min_confidence=min_confidence,
        score_abs_deadzone=score_abs_deadzone,
        path=path,
    )
    from prophecy_hit_rate_ssot_v1 import is_headline_kpi_path

    if not is_headline_kpi_path(output):
        raise ValueError(
            f"Headline KPI promotion output must be commander SSOT path, got: {output}"
        )


def rail_auto_apply_mode(rail: str, *, path: Path | None = None) -> str:
    doc = load_allowlist(path)
    rails = doc.get("rails") if isinstance(doc.get("rails"), dict) else {}
    block = rails.get(rail) if isinstance(rails.get(rail), dict) else {}
    return str(block.get("auto_apply_mode") or "none")
