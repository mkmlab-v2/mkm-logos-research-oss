#!/usr/bin/env python3
"""Load logos verse per-lane SSOT cap bind policy (B-track, FAIL-COMP-004)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "reports/logos_verse_per_lane_ssot_cap_policy_v1_latest.json"
SCHEMA = "logos_verse_per_lane_ssot_cap_policy_v1"


def load_policy(path: Path | None = None) -> dict[str, Any]:
    p = path if path is not None else DEFAULT_POLICY
    if not p.is_file():
        raise FileNotFoundError(f"missing policy: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"unexpected schema: {doc.get('schema')!r}")
    return doc


def eval_cap_overrides(policy: dict[str, Any]) -> dict[str, Any]:
    """Kwargs fragment for evaluate_report / dryrun _run_eval."""
    bind = policy.get("cap_bind") or {}
    if bind.get("clear_signoff_domain_relaxed"):
        relaxed: dict[str, float] = dict(bind.get("domain_relaxed_max_saving_overrides") or {})
    else:
        relaxed = dict(bind.get("domain_relaxed_max_saving_overrides") or {})
    general = float(bind["general_max_saving_rate"])
    sensitive = float(bind.get("sensitive_max_saving_rate", general))
    hangul = float(bind.get("hangul_max_saving_rate", general))
    return {
        "general_max_saving_rate": general,
        "sensitive_max_saving_rate": sensitive,
        "hangul_max_saving_rate": hangul,
        "domain_relaxed_max_saving_overrides": relaxed,
        "domain_relaxed_max_saving_case_allowlist": None,
        "domain_relaxed_max_saving_exclude_case_ids": frozenset(),
    }


def policy_allows_pool_mode(policy: dict[str, Any], pool_mode: str) -> bool:
    allowed = policy.get("allowed_pool_modes") or []
    return pool_mode in allowed
