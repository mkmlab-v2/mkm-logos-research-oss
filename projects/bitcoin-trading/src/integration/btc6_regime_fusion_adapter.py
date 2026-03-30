#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @MKM12-METADATA
# Type: Integration
# Vector: {S:0.6, L:0.7, K:0.8, M:0.5}
# Balance: 88
# Purpose: BTC-6 regime fusion adapter: 1차(실물) + 2차(성경) 융합 후 리스크 계수 반환.
# Keywords: BTC6, Regime, Risk, Adapter, Integration

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# WORKSPACE_ROOT 계산: projects/bitcoin-trading/src/integration -> 5단계 상위 (C:\workspace)
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent

# tools import를 위해 workspace 루트를 path에 추가 (adapter 단독 실행 시)
import sys
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

def _get_logos_core_cap() -> Optional[float]:
    """
    Logos Core(ensemble_core_v1) 로드. 있으면 2차(보) biblical 가중치 상한으로 사용할 cap 반환.
    없으면 None (기존 max_biblical 그대로). 규칙: logos-first-pipeline, regime-field-constitution.
    """
    try:
        from tools.logos import load_ensemble_core
        core_data, _ = load_ensemble_core()
        if not core_data:
            logger.debug("btc6_regime_fusion: Logos Core 없음, 2차 가중치 cap 미적용")
            return None
        distances = [v.get("distance_to_centroid") for v in core_data.values() if isinstance(v.get("distance_to_centroid"), (int, float))]
        if not distances:
            return None
        import statistics
        median_d = statistics.median(distances)
        # 시장 4D가 Core 분포보다 0.25에서 멀면 2차 보조만 더 보수적으로 (cap 0.15)
        return 0.15 if median_d < 0.2 else None
    except Exception as e:
        logger.debug("btc6_regime_fusion: Logos Core 로드 실패 err=%s", e)
        return None

# BTC-6 파이프라인 SSOT 경로 (설계 문서 기준)
REGIME_DIR = WORKSPACE_ROOT / "data" / "regimes"
REGIME_MAP_PATH = REGIME_DIR / "regime_map.json"
BIBLICAL_REGIME_MATRIX_PATH = REGIME_DIR / "biblical_regime_matrix.json"
REGIME_FUSION_POLICY_PATH = REGIME_DIR / "regime_fusion_policy.json"

# 1차 레짐별 기본 리스크 계수 (regime_overrides 없을 때 사용, 백테스트로 교체 예정)
DEFAULT_REGIME_RISK: Dict[str, float] = {
    "imf": 0.75,
    "lehman": 0.65,
    "covid": 0.70,
    "it_bubble": 0.85,
    "unknown": 1.0,
}

# 1차 실물 레짐 스키마 잠금(운영 가드)
REQUIRED_PRIMARY_REGIMES = ("imf", "it_bubble", "lehman", "covid")

def get_biblical_hypothesis_status(
    vector_4d: Dict[str, float],
    biblical_regime_path: Optional[Path] = None,
) -> bool:
    """
    2차(성경) 레짐이 현재 'hypothesis'로 매칭되는지 여부.
    AND 게이트: hypothesis일 때만 실물 피처(펀딩비/ETF) 교차 검증 필요.

    Returns:
        True if closest biblical regime has status == "hypothesis".
    """
    paths = get_default_regime_paths()
    biblical_regime_path = biblical_regime_path or paths["biblical_regime_path"]
    _bid, _vec, status = _get_closest_biblical_regime(vector_4d, biblical_regime_path)
    return status == "hypothesis"


__all__ = [
    "get_btc6_risk_multiplier",
    "get_biblical_hypothesis_status",
    "get_default_regime_paths",
    "WORKSPACE_ROOT",
    "REGIME_DIR",
    "REGIME_MAP_PATH",
    "BIBLICAL_REGIME_MATRIX_PATH",
    "REGIME_FUSION_POLICY_PATH",
]


def _load_json(path: Path) -> Dict[str, Any]:
    """JSON 파일 로드. 없거나 오류 시 빈 dict."""
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("btc6_regime_fusion: JSON 로드 실패 path=%s err=%s", path, e)
        return {}


def _vector_to_tuple(v: Dict[str, float]) -> Tuple[float, float, float, float]:
    """S,L,K,M 순서 튜플."""
    return (
        float(v.get("S", 0.0)),
        float(v.get("L", 0.0)),
        float(v.get("K", 0.0)),
        float(v.get("M", 0.0)),
    )


def _l2_distance(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
) -> float:
    """L2 거리."""
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _get_closest_biblical_regime(
    vector_4d: Dict[str, float],
    biblical_path: Path,
) -> Tuple[str, Optional[Dict[str, float]], Optional[str]]:
    """
    2차(성경) 레짐 중 vector_4d와 최근접인 레짐 ID와 벡터, status 반환.
    Returns:
        (regime_id, unified_4d_vector, status)
    """
    data = _load_json(biblical_path)
    raw_regimes = data.get("regimes") or {}
    # regimes는 JSON에서 list(배열) 또는 dict 둘 다 허용
    if isinstance(raw_regimes, list):
        regimes_iter = [(r.get("id", ""), r) for r in raw_regimes if isinstance(r, dict)]
    else:
        regimes_iter = (raw_regimes or {}).items()
    if not regimes_iter:
        return ("unknown", None, None)

    target = _vector_to_tuple(vector_4d)
    best_id = "unknown"
    best_dist = float("inf")
    best_vec: Optional[Dict[str, float]] = None
    best_status: Optional[str] = None

    for rid, r in regimes_iter:
        u4d = (r or {}).get("unified_4d_vector") or {}
        if not u4d:
            continue
        candidate = _vector_to_tuple(u4d)
        d = _l2_distance(target, candidate)
        if d < best_dist:
            best_dist = d
            best_id = rid
            best_vec = u4d
            best_status = (r or {}).get("status")

    return (best_id, best_vec, best_status)


def _is_regime_map_locked_and_valid(regime_map_path: Path) -> bool:
    """regime_map 스키마 잠금 검증. 실패 시 안전하게 1차 unknown 레짐으로 폴백한다."""
    payload = _load_json(regime_map_path)
    regimes = payload.get("regimes") if isinstance(payload, dict) else None
    if not isinstance(regimes, dict):
        logger.error("btc6_regime_fusion: regime_map schema invalid (regimes dict missing)")
        return False
    missing = [rid for rid in REQUIRED_PRIMARY_REGIMES if rid not in regimes]
    if missing:
        logger.error("btc6_regime_fusion: regime_map lock mismatch, missing=%s", missing)
        return False
    return True


def get_default_regime_paths() -> Dict[str, Path]:
    """
    BTC-6 Regime Fusion이 사용하는 SSOT 경로를 반환한다.

    설계 문서(`BTC-6_실전_트레이딩_엔진_구조_설계_2026-03-11.md`)의 2. 데이터 경로(SSOT) 표와 4. 폴더 구조를
    코드 차원에서 한 번 더 고정하기 위한 헬퍼이다.
    """
    return {
        "regime_map_path": REGIME_MAP_PATH,
        "biblical_regime_path": BIBLICAL_REGIME_MATRIX_PATH,
        "fusion_policy_path": REGIME_FUSION_POLICY_PATH,
    }


def get_btc6_risk_multiplier(
    vector_4d: Dict[str, float],
    psi_score: float,
    regime_map_path: Optional[Path] = None,
    biblical_regime_path: Optional[Path] = None,
    fusion_policy_path: Optional[Path] = None,
) -> float:
    """
    1차 레짐(실물) + 2차 레짐(성경, 보조) 융합 후 리스크 계수 반환.

    - 1차: regime_map.json으로 최근접 레짐 → base multiplier (regime_overrides 또는 기본표).
    - 2차: biblical_regime_matrix.json으로 최근접 레짐 → hypothesis_trigger_allowed·alignment 적용 후
      max_biblical_weight 이내로 보정. 2차는 트리거용이 아닌 보조만.
    - 최종 multiplier는 [0.2, 1.5]로 클램프.

    Args:
        vector_4d: 현재 BTC 시장 4D 벡터 (S, L, K, M).
        psi_score: PSI(예언적 주기성 지수). 미사용 시 0.0 전달 가능.
        regime_map_path: 1차 레짐 JSON 경로. None이면 SSOT 기본.
        biblical_regime_path: 2차 레짐 JSON 경로. None이면 SSOT 기본.
        fusion_policy_path: Fusion 정책 JSON 경로. None이면 SSOT 기본.

    Returns:
        float: 리스크 multiplier (0.2 ~ 1.5).
    """
    paths = get_default_regime_paths()
    regime_map_path = regime_map_path or paths["regime_map_path"]
    biblical_regime_path = biblical_regime_path or paths["biblical_regime_path"]
    fusion_policy_path = fusion_policy_path or paths["fusion_policy_path"]

    policy = _load_json(fusion_policy_path)
    # 정책: 설계안 형식(regime_overrides, biblical_overrides) 또는 현재 형식(global, domain_overrides)
    domain = (policy.get("domain_overrides") or {}).get("trading") or {}
    global_ = policy.get("global") or {}
    regime_overrides = policy.get("regime_overrides") or domain.get("regime_overrides") or {}
    biblical_overrides = policy.get("biblical_overrides") or domain.get("biblical_overrides") or {}
    default_risk = float(
        policy.get("default_risk_multiplier")
        or domain.get("default_risk_multiplier")
        or global_.get("default_risk_multiplier")
        or 1.0
    )
    # 캘리브 결과가 있으면 recommended_multiplier로 default_risk 덮어쓰기
    # 단, 품질 게이트 실패(safe_mode_forced)면 1.0 강제
    calibration_path_rel = global_.get("btc6_calibration_path")
    if calibration_path_rel:
        calibration_path = (WORKSPACE_ROOT / calibration_path_rel).resolve()
        if calibration_path.is_file():
            cal = _load_json(calibration_path)
            quality = cal.get("quality_metrics") or {}
            safe_mode_forced = bool(quality.get("safe_mode_forced", False))
            if safe_mode_forced:
                default_risk = 1.0
                logger.warning("btc6_regime_fusion: quality gate failed -> safe_mode multiplier=1.0 path=%s", calibration_path)
            else:
                rec = cal.get("recommended_multiplier")
                if rec is not None:
                    default_risk = float(rec)
                    logger.debug("btc6_regime_fusion: 캘리브 반영 default_risk=%.3f path=%s", default_risk, calibration_path)
    max_biblical = float(
        global_.get("max_biblical_weight") or domain.get("max_biblical_weight") or 0.3
    )
    # Logos Core(ensemble_core) 있으면 2차(보) 상한만 더 보수적으로 적용 (트리거 아님)
    logos_cap = _get_logos_core_cap()
    if logos_cap is not None:
        max_biblical = min(max_biblical, logos_cap)
    alignment_threshold = float(
        global_.get("alignment_threshold") or domain.get("alignment_threshold") or 0.5
    )
    hypothesis_trigger_allowed = global_.get("hypothesis_trigger_allowed") is True or domain.get(
        "hypothesis_trigger_allowed"
    ) is True

    # 1차 레짐 (잠금된 스키마 검증 실패 시 unknown 폴백)
    try:
        if not _is_regime_map_locked_and_valid(regime_map_path):
            primary_id = "unknown"
            primary_vec = None
        else:
            from tools.prophecy.regime_matcher import get_closest_regime
            primary = get_closest_regime(vector_4d, regime_map_path)
            primary_id = (primary or {}).get("regime_id") or "unknown"
            primary_fingerprint = (primary or {}).get("fingerprint") or {}
            primary_vec = primary_fingerprint.get("unified_4d_vector") if isinstance(
                primary_fingerprint, dict
            ) else None
    except Exception as e:
        logger.warning("btc6_regime_fusion: 1차 레짐 매칭 실패 err=%s", e)
        primary_id = "unknown"
        primary_vec = None

    base = float(
        (regime_overrides.get(primary_id) or {}).get("risk_multiplier")
        or DEFAULT_REGIME_RISK.get(primary_id)
        or DEFAULT_REGIME_RISK.get("unknown")
        or default_risk
    )

    # 2차 레짐 (보조만, 트리거 사용 금지)
    biblical_id, biblical_vec, biblical_status = _get_closest_biblical_regime(
        vector_4d, biblical_regime_path
    )
    biblical_effect = 0.0
    if biblical_vec is not None and primary_vec is not None:
        if biblical_status == "hypothesis" and not hypothesis_trigger_allowed:
            pass  # 2차 기여 0
        else:
            sim = 1.0 / (1.0 + _l2_distance(_vector_to_tuple(primary_vec), _vector_to_tuple(biblical_vec)))
            if sim >= alignment_threshold:
                w = (biblical_overrides.get(biblical_id) or {}).get("weight", 0.5)
                biblical_effect = min(max_biblical, float(w))

    # base를 2차로 약간 낮출 수 있음: base * (1 - biblical_effect) → 위기일 때 더 보수적
    multiplier = base * (1.0 - biblical_effect)
    min_mul = float(global_.get("risk_multiplier_min") or domain.get("risk_multiplier_min") or 0.5)
    max_mul = float(global_.get("risk_multiplier_max") or domain.get("risk_multiplier_max") or 1.5)
    multiplier = max(min_mul, min(max_mul, multiplier))

    logger.info(
        "BTC-6 Regime Fusion: primary=%s base=%.3f biblical=%s effect=%.3f multiplier=%.3f",
        primary_id, base, biblical_id, biblical_effect, multiplier,
    )
    return round(multiplier, 4)

