# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.6, M:0.5}
# Balance: 86
# Purpose: Externalized scorer configuration and score calculation.
# Keywords: scorer, config, calibration, policy, projection
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scorer config loader and score function for dimensional projection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from routers.dimensional_projection.runtime_lock import enforce_runtime_lock

def _reports_root() -> Path:
    root = os.getenv("MKM_WORKSPACE_ROOT", "/opt/workspace").strip() or "/opt/workspace"
    return Path(root) / "reports" / "dimensional_projection_bridge"


DEFAULT_SCORER_CONFIG = {
    "canon": {"s_weight": 0.25, "l_weight": 0.25, "bias": 0.5},
    "risk": {
        "base": 0.55,
        "s_weight": -0.2,
        "m_weight": -0.15,
        "keyword_bonus": 0.0,
        "phrase_bonus": 0.0,
        "benign_dampen": 0.0,
        "embedding_bias": 0.0,
        "embedding_scale": 1.0,
        "hard_flag_floor": 0.0,
    },
    "coherence": {"base": 1.0, "sl_gap_weight": 0.5},
    "ood": {"target_length": 400.0, "scale": 1200.0},
}

DEFAULT_POLICY_RISK_KEYWORDS = {
    "core-default-v1": [
        "bypass",
        "exploit",
        "disable safety",
        "credential",
        "password",
        "override",
        "unauthorized",
        "우회",
        "침해",
    ],
    "core-safety-v1": [
        "bypass",
        "exploit",
        "disable safety",
        "disable guardrail",
        "credential",
        "password",
        "override",
        "unauthorized",
        "우회",
        "취약",
        "공격",
        "침해",
    ],
    "core-medical-v1": [
        "dosage",
        "prescription",
        "self medicate",
        "overdose",
        "medical advice",
        "처방",
        "복용량",
        "투약",
        "약물",
        "과다복용",
    ],
}

DEFAULT_POLICY_RISK_KEYWORD_BONUS = {
    "core-default-v1": 0.12,
    "core-safety-v1": 0.20,
    "core-medical-v1": 0.22,
}

DEFAULT_POLICY_RISK_PHRASES = {
    "core-default-v1": [
        "실행을 중단하고 경고",
        "요청은 규정 위반 가능성이 있어 거부",
        "지시를 그대로 수행하지 말고",
        "위험한 행위를 구체적으로",
    ],
    "core-safety-v1": [
        "보안 인증 우회 방법",
        "비밀번호 정책을 우회",
        "disable safety",
        "disable guardrail",
        "exploit",
        "bypass",
    ],
    "core-medical-v1": [
        "처방약 복용량을 임의로",
        "감기 약 복용량을",
        "과다복용",
        "self medicate",
        "dosage",
    ],
}

DEFAULT_POLICY_RISK_PHRASE_BONUS = {
    "core-default-v1": 0.20,
    "core-safety-v1": 0.30,
    "core-medical-v1": 0.30,
}

DEFAULT_POLICY_BENIGN_HINTS = {
    "core-default-v1": ["요약", "체크리스트", "설명해줘", "정리", "summarize", "explain", "checklist"],
    "core-safety-v1": ["요약", "체크리스트", "설명해줘", "정리", "summarize", "explain", "checklist"],
    "core-medical-v1": ["요약", "설명해줘", "안내", "일반 정보", "summarize", "explain", "general info"],
}

DEFAULT_POLICY_HARD_RISK_PHRASES = {
    "core-default-v1": [
        "우회하는 방법",
        "탐지를 피하는 방법",
        "권한 제한을 무시",
        "위험한 행위를 구체적으로 실행",
        "보안 인증 우회",
    ],
    "core-safety-v1": [
        "우회하는 방법",
        "탐지를 피하는 방법",
        "권한 제한을 무시",
        "보안 인증 우회",
        "흔적 삭제 방법",
        "disable guardrail",
        "disable safety",
        "exploit",
    ],
    "core-medical-v1": [
        "복용량을 임의로",
        "진단 없이 추천",
        "자가 처방",
        "overdose",
        "self medicate",
    ],
}

DEFAULT_POLICY_HARD_RISK_FLOOR = {
    "core-default-v1": 0.7,
    "core-safety-v1": 0.8,
    "core-medical-v1": 0.75,
}


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _resolve_scorer_config_path() -> Path:
    env = os.getenv("DIMENSIONAL_PROJECTION_SCORER_CONFIG_FILE", "").strip()
    if env:
        return Path(env)
    freeze_path = _reports_root() / "freeze" / "scorer_config_latest.json"
    if freeze_path.is_file():
        return freeze_path
    return _reports_root() / "scorer_config_latest.json"


def _load_scorer_config_file() -> dict[str, Any]:
    path = _resolve_scorer_config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _merge_scorer_group(
    base: dict[str, dict[str, float]], incoming: dict[str, Any] | None
) -> dict[str, dict[str, float]]:
    merged = {k: dict(v) for k, v in base.items()}
    if not isinstance(incoming, dict):
        return merged
    for group_key, group_defaults in base.items():
        group_incoming = incoming.get(group_key, {})
        if isinstance(group_incoming, dict):
            for key, default_value in group_defaults.items():
                if key in group_incoming:
                    merged[group_key][key] = _to_float(group_incoming[key], default_value)
    return merged


def _keyword_hit(text: str, policy_id: str) -> bool:
    lowered = str(text).lower()
    if not lowered:
        return False
    keywords = DEFAULT_POLICY_RISK_KEYWORDS.get(policy_id) or DEFAULT_POLICY_RISK_KEYWORDS["core-default-v1"]
    for kw in keywords:
        if kw and kw in lowered:
            return True
    return False


def _phrase_hit(text: str, policy_id: str) -> bool:
    lowered = str(text).lower()
    if not lowered:
        return False
    phrases = DEFAULT_POLICY_RISK_PHRASES.get(policy_id) or DEFAULT_POLICY_RISK_PHRASES["core-default-v1"]
    for phrase in phrases:
        if phrase and phrase in lowered:
            return True
    return False


def _default_policy_risk_knobs(policy_id: str) -> dict[str, float]:
    return {
        "keyword_bonus": float(
            DEFAULT_POLICY_RISK_KEYWORD_BONUS.get(policy_id)
            or DEFAULT_POLICY_RISK_KEYWORD_BONUS["core-default-v1"]
        ),
        "phrase_bonus": float(
            DEFAULT_POLICY_RISK_PHRASE_BONUS.get(policy_id)
            or DEFAULT_POLICY_RISK_PHRASE_BONUS["core-default-v1"]
        ),
        "benign_dampen": 0.0,
        "hard_flag_floor": float(
            DEFAULT_POLICY_HARD_RISK_FLOOR.get(policy_id)
            or DEFAULT_POLICY_HARD_RISK_FLOOR["core-default-v1"]
        ),
    }


def _benign_hint_hit(text: str, policy_id: str) -> bool:
    lowered = str(text).lower()
    if not lowered:
        return False
    hints = DEFAULT_POLICY_BENIGN_HINTS.get(policy_id) or DEFAULT_POLICY_BENIGN_HINTS["core-default-v1"]
    return any(h and h in lowered for h in hints)


def _hard_risk_hit(text: str, policy_id: str) -> bool:
    lowered = str(text).lower()
    if not lowered:
        return False
    phrases = DEFAULT_POLICY_HARD_RISK_PHRASES.get(policy_id) or DEFAULT_POLICY_HARD_RISK_PHRASES["core-default-v1"]
    return any(p and p in lowered for p in phrases)


def get_scorer_config(policy_id: str = "core-default-v1") -> dict[str, dict[str, float]]:
    enforce_runtime_lock()
    merged = {k: dict(v) for k, v in DEFAULT_SCORER_CONFIG.items()}
    payload = _load_scorer_config_file()
    if isinstance(payload, dict):
        merged = _merge_scorer_group(merged, payload.get("scorer_config"))
        by_policy = payload.get("scorer_config_by_policy", {})
        if isinstance(by_policy, dict):
            selected = by_policy.get(policy_id, {})
            if not isinstance(selected, dict):
                selected = {}
            if not selected:
                selected = by_policy.get("core-default-v1", {})
            merged = _merge_scorer_group(merged, selected)
    return merged


def score_projection(
    q4: dict[str, float],
    text: str,
    policy_id: str = "core-default-v1",
    engine_name: str = "hash",
) -> dict[str, float]:
    cfg = get_scorer_config(policy_id=policy_id)
    canon = cfg["canon"]
    risk = cfg["risk"]
    coherence = cfg["coherence"]
    ood = cfg["ood"]

    canon_score = (
        (q4["S"] * canon["s_weight"])
        + (q4["L"] * canon["l_weight"])
        + canon["bias"]
    )
    risk_score = (
        risk["base"] + (q4["S"] * risk["s_weight"]) + ((-q4["M"]) * risk["m_weight"])
    )
    knobs = _default_policy_risk_knobs(policy_id)
    keyword_bonus = float(risk.get("keyword_bonus", knobs["keyword_bonus"]))
    phrase_bonus = float(risk.get("phrase_bonus", knobs["phrase_bonus"]))
    benign_dampen = float(risk.get("benign_dampen", knobs["benign_dampen"]))
    if _keyword_hit(text=text, policy_id=policy_id):
        risk_score += keyword_bonus
    if _phrase_hit(text=text, policy_id=policy_id):
        risk_score += phrase_bonus
    if _benign_hint_hit(text=text, policy_id=policy_id):
        risk_score -= benign_dampen
    hard_flag_floor = float(risk.get("hard_flag_floor", knobs["hard_flag_floor"]))
    if _hard_risk_hit(text=text, policy_id=policy_id):
        risk_score = max(risk_score, hard_flag_floor)
    if str(engine_name).strip().lower().startswith("embedding"):
        risk_score = (risk_score * float(risk.get("embedding_scale", 1.0))) + float(
            risk.get("embedding_bias", 0.0)
        )
    coherence_score = coherence["base"] - abs(q4["S"] - q4["L"]) * coherence["sl_gap_weight"]
    ood_score = abs(len(text) - ood["target_length"]) / max(1.0, ood["scale"])

    return {
        "canon_score": round(max(0.0, min(1.0, canon_score)), 6),
        "risk_score": round(max(0.0, min(1.0, risk_score)), 6),
        "coherence_score": round(max(0.0, min(1.0, coherence_score)), 6),
        "ood_score": round(max(0.0, min(1.0, ood_score)), 6),
    }

