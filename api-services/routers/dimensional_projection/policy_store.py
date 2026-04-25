# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.8}
# Balance: 88
# Purpose: Externalize policy thresholds for governor decisions.
# Keywords: policy, threshold, config, env, json
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Policy store for dimensional projection governor."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from routers.dimensional_projection.runtime_lock import enforce_runtime_lock

DEFAULT_POLICY = {
    "risk_block_threshold": 0.8,
    "risk_revise_threshold": 0.65,
    "ood_revise_threshold": 0.7,
    "canon_min_threshold": 0.45,
    "coherence_min_threshold": 0.5,
}


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _reports_root() -> Path:
    root = os.getenv("MKM_WORKSPACE_ROOT", "/opt/workspace").strip() or "/opt/workspace"
    return Path(root) / "reports" / "dimensional_projection_bridge"


def _resolve_policy_file() -> Path:
    env = os.getenv("DIMENSIONAL_PROJECTION_POLICY_FILE", "").strip()
    if env:
        return Path(env)
    runtime_path = _reports_root() / "policies_latest.json"
    if runtime_path.is_file():
        return runtime_path
    return Path(__file__).with_name("policies.default.json")


def _load_policy_file() -> dict[str, Any]:
    path = _resolve_policy_file()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_calibrated_policy_file() -> Path:
    env = os.getenv("DIMENSIONAL_PROJECTION_CALIBRATED_POLICY_FILE", "").strip()
    if env:
        return Path(env)
    freeze_path = _reports_root() / "freeze" / "policies_calibrated_latest.json"
    if freeze_path.is_file():
        return freeze_path
    return _reports_root() / "policies_calibrated_latest.json"


def _load_calibrated_policy_file() -> dict[str, Any]:
    path = _resolve_calibrated_policy_file()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_policy_thresholds(policy_id: str) -> dict[str, float]:
    """
    Resolve thresholds with precedence:
    1) Built-in default
    2) Policy file override by policy_id
    3) Env var overrides
    """
    enforce_runtime_lock()
    merged = dict(DEFAULT_POLICY)

    payload = _load_policy_file()
    if isinstance(payload, dict):
        policy_map = payload.get("policies", {})
        if isinstance(policy_map, dict):
            selected = policy_map.get(policy_id, {})
            if not isinstance(selected, dict):
                selected = {}
            if not selected:
                selected = policy_map.get("core-default-v1", {})
            if isinstance(selected, dict):
                for key in DEFAULT_POLICY:
                    if key in selected:
                        merged[key] = _to_float(selected[key], merged[key])

    calibrated = _load_calibrated_policy_file()
    if isinstance(calibrated, dict):
        cal_map = calibrated.get("policies", {})
        if isinstance(cal_map, dict):
            selected_cal = cal_map.get(policy_id, {})
            if not isinstance(selected_cal, dict):
                selected_cal = {}
            if not selected_cal:
                selected_cal = cal_map.get("core-default-v1", {})
            if isinstance(selected_cal, dict):
                for key in DEFAULT_POLICY:
                    if key in selected_cal:
                        merged[key] = _to_float(selected_cal[key], merged[key])

    env_map = {
        "risk_block_threshold": "DIMENSIONAL_PROJECTION_RISK_BLOCK_THRESHOLD",
        "risk_revise_threshold": "DIMENSIONAL_PROJECTION_RISK_REVISE_THRESHOLD",
        "ood_revise_threshold": "DIMENSIONAL_PROJECTION_OOD_REVISE_THRESHOLD",
        "canon_min_threshold": "DIMENSIONAL_PROJECTION_CANON_MIN_THRESHOLD",
        "coherence_min_threshold": "DIMENSIONAL_PROJECTION_COHERENCE_MIN_THRESHOLD",
    }
    for key, env_name in env_map.items():
        raw = os.getenv(env_name, "").strip()
        if raw:
            merged[key] = _to_float(raw, merged[key])
    return merged


def list_policy_thresholds() -> dict[str, dict[str, float]]:
    """Return available policy profiles with normalized thresholds."""
    payload = _load_policy_file()
    policy_ids: list[str] = []
    if isinstance(payload, dict):
        policy_map = payload.get("policies", {})
        if isinstance(policy_map, dict):
            policy_ids = [k for k in policy_map.keys() if isinstance(k, str) and k.strip()]

    if "core-default-v1" not in policy_ids:
        policy_ids.insert(0, "core-default-v1")

    result: dict[str, dict[str, float]] = {}
    for policy_id in policy_ids:
        result[policy_id] = get_policy_thresholds(policy_id)
    return result

