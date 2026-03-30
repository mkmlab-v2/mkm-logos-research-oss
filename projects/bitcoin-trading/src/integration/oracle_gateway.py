#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PGAE Oracle Gateway: PMI-Nitro 주문 실행 직전 14B 검증

- 입력: signal, price, confidence, leverage_multiplier, signal_data
- 예언 컨텍스트 로드 후 14B에 "APPROVE / REDUCE / REJECT" 판단 요청
- 출력: {"verdict": "APPROVE"|"REDUCE"|"REJECT", "multiplier": float}
- REDUCE 시 multiplier(0.0~1.0)를 포지션 크기에 적용

14B 자연어 본문의 가격·수치 주장은 AGENTS.md 기준 Tier 3(단독 근거 금지).
게이트 판정·로그(JSON)만 운용 근거로 취급한다.
"""
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent


def _inference_failure_verdict(loader: Any) -> Dict[str, Any]:
    """
    14B 추론 예외 또는 빈 응답 시 반환값.
    trading_config.yaml 의 oracle_gateway.on_inference_failure 가 reject 이면 주문 스킵.
    """
    mode = "approve"
    try:
        if loader is not None and getattr(loader, "config", None):
            og = loader.config.get("oracle_gateway") or {}
            if isinstance(og, dict):
                mode = str(og.get("on_inference_failure", "approve")).lower().strip()
    except Exception:
        pass
    if mode == "reject":
        return {"verdict": "REJECT", "multiplier": 0.0}
    return {"verdict": "APPROVE", "multiplier": 1.0}
DEFAULT_CONFIG = WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml"
METRICS_DIR = WORKSPACE_ROOT / "memory" / "metrics" / "trading"

try:
    from src.integration.omni_oracle_contract import (
        CONTRACT_VERSION as OMNI_CONTRACT_VERSION,
        TRANSITION_PRIORS_KEYS,
    )
except Exception:
    OMNI_CONTRACT_VERSION = "omni-oracle.v1"
    TRANSITION_PRIORS_KEYS = [
        "current_regime_state",
        "markov_transition",
        "likelihood",
        "prophecy",
        "prior_bias",
    ]


def _ensure_metrics_dir() -> None:
    """
    KPI용 메트릭 디렉토리 생성 (없으면 생성).
    """
    try:
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.debug("Oracle Gateway: METRICS_DIR 생성 실패(무시): %s", e)


def _log_oracle_kpi(
    prophecy: Dict[str, Any],
    oracle_raw_response: Optional[str],
    oracle_result: Dict[str, Any],
) -> None:
    """
    Oracle Gateway 호출 1회에 대한 KPI를 File-Based Memory에 JSON으로 기록.

    Sharpe/PNL 등 정교한 지표는 별도 집계 스크립트에서 계산하고,
    여기서는 예언 컨텍스트와 14B verdict 중심의 최소 정보만 남긴다.

    PII 검증: memory/metrics/* 저장 전 sanitize_for_logging 적용 (컴플라이언스 정책).
    """
    try:
        import json

        from tools.core.pii_validator import sanitize_for_logging, validate_kpi_payload

        _ensure_metrics_dir()

        now = datetime.now()
        timestamp = now.isoformat()
        date_str = now.strftime("%Y-%m-%d")
        run_id = now.strftime("%Y%m%d-%H%M%S-oracle-01")

        payload: Dict[str, Any] = {
            "timestamp": timestamp,
            "date": date_str,
            "engine": "oracle_gateway",
            "domain": "bitcoin-trading",
            "run_id": run_id,
            "version": "v1.0",
            "prophecy": {
                "direction": prophecy.get("prophecy_direction") or "NEUTRAL",
                "divine_distance": prophecy.get("divine_distance") or 0.0,
                "crisis_level": prophecy.get("crisis_level") or "UNKNOWN",
                "today_summary": prophecy.get("today_summary") or "",
                # hit-rate는 일/주/월 집계 스크립트에서 계산
            },
            "oracle": {
                "verdict": oracle_result.get("verdict", "APPROVE"),
                "multiplier": oracle_result.get("multiplier", 1.0),
                "raw_response_preview": (oracle_raw_response or "")[:160],
            },
        }

        # PII 검증 및 정제 (memory/metrics/* 저장 전 필수)
        ok, violations = validate_kpi_payload(payload)
        if not ok:
            logger.debug("Oracle Gateway: PII 검증 위반 필드 제거 후 기록: %s", violations)
        payload = sanitize_for_logging(payload)

        out_path = METRICS_DIR / f"oracle_{now.strftime('%Y%m%d_%H%M%S')}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.debug("Oracle Gateway: KPI 메트릭 기록 완료: %s", out_path)
    except Exception as e:
        # 메트릭 로깅 실패는 주문 로직에 영향을 주지 않도록 조용히 기록만 남긴다.
        logger.debug("Oracle Gateway: KPI 메트릭 기록 실패(무시): %s", e)


def _validate_omni_contract_payload(signal_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optional contract validation hook for post-fusion Omni-Oracle payloads.

    Expected shape in signal_data:
      - signal_data["omni_oracle_request"] (dict)
      - signal_data["omni_oracle_request"]["contract_version"] == OMNI_CONTRACT_VERSION
      - signal_data["omni_oracle_request"]["priors"] includes TRANSITION_PRIORS_KEYS
    """
    req = signal_data.get("omni_oracle_request")
    if not isinstance(req, dict):
        return {"present": False, "valid": True, "reason": "missing_optional_payload"}

    received_version = str(req.get("contract_version", "")).strip()
    if received_version != OMNI_CONTRACT_VERSION:
        return {
            "present": True,
            "valid": False,
            "reason": "contract_version_mismatch",
            "expected": OMNI_CONTRACT_VERSION,
            "received": received_version,
        }

    priors = req.get("priors")
    if not isinstance(priors, dict):
        return {"present": True, "valid": False, "reason": "priors_missing_or_invalid"}

    missing = [k for k in TRANSITION_PRIORS_KEYS if k not in priors]
    if missing:
        return {"present": True, "valid": False, "reason": "priors_missing_keys", "missing_keys": missing}

    return {"present": True, "valid": True, "reason": "ok"}


def oracle_gateway_verify(
    signal: str,
    price: float,
    confidence: float,
    leverage_multiplier: float,
    signal_data: Dict[str, Any],
    config_file: Optional[Path] = None,
    timeout_sec: int = 90,
) -> Dict[str, Any]:
    """
    PMI-Nitro 주문 실행 직전 14B 검증 (Oracle Gateway).

    Args:
        signal: BUY / SELL / HOLD
        price: 현재 가격
        confidence: 신뢰도 (0.0~1.0)
        leverage_multiplier: 가상 레버리지 배율
        signal_data: cited_trading_wisdom, quaternion_insight, vector_4d 등
        config_file: trading_config.yaml 경로 (None이면 기본값)
        timeout_sec: 14B 추론 타임아웃

    Returns:
        {"verdict": "APPROVE"|"REDUCE"|"REJECT", "multiplier": float}
        - APPROVE: 그대로 실행
        - REDUCE: multiplier(0.0~1.0)를 leverage_multiplier에 곱해 실행
        - REJECT: 주문 스킵
    """
    result: Dict[str, Any] = {"verdict": "APPROVE", "multiplier": 1.0}
    loader: Optional[Any] = None

    # 14B 호출 경로 로드
    try:
        from src.config.config_loader import ConfigLoader
        cfg = config_file or DEFAULT_CONFIG
        loader = ConfigLoader(cfg)
        loader.load()
        call_path = loader.get_14b_4d_native_call_path()
    except Exception as e:
        logger.debug("Oracle Gateway: ConfigLoader 실패, APPROVE 통과: %s", e)
        return result

    if not call_path:
        logger.debug("Oracle Gateway: 14B 비활성화, APPROVE 통과")
        return result

    # get_14b_advisory import
    try:
        from src.llm.llm_14b_advisory import get_14b_advisory
    except ImportError:
        logger.debug("Oracle Gateway: get_14b_advisory import 실패, APPROVE 통과")
        return result

    # 예언 컨텍스트 로드
    try:
        from src.integration.prophecy_sync import load_prophecy_context
        prophecy = load_prophecy_context()
    except Exception as e:
        logger.warning("Oracle Gateway: prophecy_sync 로드 실패: %s", e)
        prophecy = {
            "divine_distance": 0.0,
            "crisis_level": "UNKNOWN",
            "prophecy_direction": "NEUTRAL",
            "today_summary": "",
        }

    # Omni-Oracle contract validation hook (optional payload)
    contract_check = _validate_omni_contract_payload(signal_data)
    if contract_check.get("present") and not contract_check.get("valid"):
        logger.warning("⚠️ Omni-Oracle contract 검증 실패: %s", contract_check)

    # 14B 프롬프트 구성
    direction = prophecy.get("prophecy_direction") or "NEUTRAL"
    distance = prophecy.get("divine_distance") or 0.0
    summary = prophecy.get("today_summary") or ""
    crisis = prophecy.get("crisis_level") or "UNKNOWN"

    prompt = (
        f"[Oracle Gateway] PMI-Nitro says {signal} (confidence={confidence:.2f}, leverage_multiplier={leverage_multiplier:.2f}). "
        f"Prophecy: direction={direction}, Divine Distance={distance:.4f}, crisis={crisis}. "
        f"OmniContract: {contract_check.get('reason', 'unknown')}. "
        f"Today: {summary[:120] if summary else 'N/A'}. "
        "Answer ONLY: APPROVE or REDUCE or REJECT. "
        "If REDUCE, add one number 0.0~1.0 (e.g. REDUCE 0.5)."
    )

    try:
        raw = get_14b_advisory(prompt, call_path, timeout_sec=timeout_sec)
    except Exception as e:
        result = _inference_failure_verdict(loader)
        if result.get("verdict") == "REJECT":
            logger.warning("Oracle Gateway: 14B 호출 실패 → REJECT (on_inference_failure=reject): %s", e)
        else:
            logger.warning("Oracle Gateway: 14B 호출 실패, APPROVE 통과: %s", e)
        _log_oracle_kpi(prophecy, oracle_raw_response=None, oracle_result=result)
        return result

    if not raw or not isinstance(raw, str):
        result = _inference_failure_verdict(loader)
        if result.get("verdict") == "REJECT":
            logger.info("Oracle Gateway: 14B 응답 없음 → REJECT (on_inference_failure=reject)")
        else:
            logger.debug("Oracle Gateway: 14B 응답 없음, APPROVE 통과")
        _log_oracle_kpi(prophecy, oracle_raw_response=None, oracle_result=result)
        return result

    raw_upper = raw.strip().upper()

    # REJECT 우선
    if "REJECT" in raw_upper:
        result["verdict"] = "REJECT"
        result["multiplier"] = 0.0
        logger.info("🔴 Oracle Gateway: REJECT - %s", raw[:80])
        _log_oracle_kpi(prophecy, oracle_raw_response=raw, oracle_result=result)
        return result

    # REDUCE + multiplier 파싱
    if "REDUCE" in raw_upper:
        result["verdict"] = "REDUCE"
        # 0.0~1.0 숫자 추출 (REDUCE 0.5, 0.5, REDUCE: 0.7 등)
        nums = re.findall(r"0?\.\d+|1\.0|\b1\b", raw)
        mult = 0.5  # 기본값
        if nums:
            try:
                mult = max(0.0, min(1.0, float(nums[0])))
            except ValueError:
                pass
        result["multiplier"] = mult
        logger.info("🟡 Oracle Gateway: REDUCE %.2f - %s", mult, raw[:80])
        _log_oracle_kpi(prophecy, oracle_raw_response=raw, oracle_result=result)
        return result

    # APPROVE
    result["verdict"] = "APPROVE"
    result["multiplier"] = 1.0
    logger.info("🟢 Oracle Gateway: APPROVE - %s", raw[:80])
    _log_oracle_kpi(prophecy, oracle_raw_response=raw, oracle_result=result)
    return result
