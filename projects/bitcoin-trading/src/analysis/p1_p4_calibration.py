#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.3, L:0.7, K:0.6, M:0.3}
# Balance: 84
# Purpose: P1→P4 교정 레이어의 스켈레톤. 현재는 신뢰도(확률)를 안전하게 클램프하는 형태의 아이덴티티 매핑으로 동작한다.
# Keywords: calibration, P1, P4, probability, confidence

from __future__ import annotations

from typing import Union, Any, Dict, Optional
from pathlib import Path
from math import sqrt
import json
import logging


Number = Union[float, int]

logger = logging.getLogger(__name__)

# 전역: 향후 P1→P4 캘리브레이션 파라미터 (없으면 None)
_P1_P4_MODEL: Optional[Dict[str, Any]] = None


def _load_p1_p4_model(model_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    P1→P4 수학적 교정 모델을 JSON에서 로드하는 진입점.

    현재는 스켈레톤:
      - 파일이 없거나 파싱 실패 시 None 반환 (아이덴티티 클램프 유지)
      - 이후 Phase에서 실제 파라미터/테이블/다항식 등을 사용하도록 확장
    """
    global _P1_P4_MODEL

    if _P1_P4_MODEL is not None:
        return _P1_P4_MODEL

    if model_path is None:
        # 기본 위치 예시: projects/bitcoin-trading/data/p1_p4_calibration_model.json
        workspace_root = Path(__file__).parent.parent.parent.parent
        model_path = (
            workspace_root
            / "projects"
            / "bitcoin-trading"
            / "data"
            / "p1_p4_calibration_model.json"
        )

    if not model_path.exists():
        logger.info(
            "P1→P4 calibration model not found (%s). "
            "identity clamp(0.0~1.0)로 동작합니다.",
            model_path,
        )
        _P1_P4_MODEL = None
        return None

    try:
        with model_path.open("r", encoding="utf-8") as f:
            _P1_P4_MODEL = json.load(f)
        logger.info("✅ P1→P4 calibration model 로드 완료: %s", model_path)
    except Exception as e:
        logger.warning("⚠️ P1→P4 calibration model 로드 실패(%s): %s", model_path, e)
        _P1_P4_MODEL = None

    return _P1_P4_MODEL


def _apply_model_confidence(p1: float, model: Dict[str, Any]) -> float:
    """
    로드된 모델을 이용해 P1 스칼라 신뢰도를 보정하는 자리.

    현재는 스켈레톤:
      - 향후 model["knots"], model["coeffs"] 등을 이용한
        비선형 맵핑/테이블 룩업/보간 등을 구현.
      - 지금은 값 변경 없이 그대로 반환.
    """
    # TODO: Phase 2에서 실제 보정 로직 구현
    return p1


def calibrate_confidence(p1: Number) -> float:
    """
    P1→P4 교정 레이어 (스칼라 신뢰도 버전).

    현재 구현:
      1) 입력값을 float로 캐스팅
      2) (선택) p1_p4_calibration_model.json을 로드해 비선형 보정 시도
      3) 최종적으로 0.0~1.0 범위로 안전하게 클램프

    Phase 1:
      - 파일이 없으면 기존과 동일한 아이덴티티 클램프만 수행
    Phase 2:
      - _apply_model_confidence에서 실제 P1→P4 수학적 교정 로직 연결
    """
    try:
        value = float(p1)
    except Exception:
        value = 0.0

    model = _load_p1_p4_model()
    if model is not None:
        try:
            value = _apply_model_confidence(value, model)
        except Exception as e:
            logger.debug("P1→P4 모델 보정 실패(무시): %s", e)

    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def analyze_equilibrium(vector_4d: Dict[str, float]) -> Dict[str, float]:
    """
    통일장 4D 평형 관점에서 간단한 진단 지표를 계산하는 유틸리티.

    이 함수는 트레이딩 로직을 직접 변경하지 않고,
    로그/리포트용으로 λ, 0.25 근접도 등을 수치적으로만 제공하는 것을 목표로 한다.
    (물리적/신학적 해석은 이 레벨에서 단정하지 않는다.)

    Args:
        vector_4d: {"S": float, "L": float, "K": float, "M": float} 형태의 4D 벡터.

    Returns:
        {
          "lambda": float,              # 0.25 센트로이드로부터의 정규화 거리
          "distance_4d": float,         # 단순 유클리드 거리
          "avg_abs_deviation": float,   # 각 축이 0.25에서 얼마나 벗어났는지의 평균 |편차|
        }
    """
    s = float(vector_4d.get("S", 0.25))
    l = float(vector_4d.get("L", 0.25))
    k = float(vector_4d.get("K", 0.25))
    m = float(vector_4d.get("M", 0.25))

    ds = s - 0.25
    dl = l - 0.25
    dk = k - 0.25
    dm = m - 0.25

    distance_4d = sqrt(ds * ds + dl * dl + dk * dk + dm * dm)
    max_theoretical = sqrt(4 * (0.25 ** 2)) or 1.0
    lambda_value = distance_4d / max_theoretical

    avg_abs_deviation = (abs(ds) + abs(dl) + abs(dk) + abs(dm)) / 4.0

    return {
        "lambda": float(lambda_value),
        "distance_4d": float(distance_4d),
        "avg_abs_deviation": float(avg_abs_deviation),
    }


__all__ = ["calibrate_confidence", "analyze_equilibrium"]

