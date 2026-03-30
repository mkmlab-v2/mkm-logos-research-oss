#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.4, L:0.8, K:0.5, M:0.3}
# Balance: 78
# Purpose: AND 게이트 — 2차(성경) hypothesis 시 실물 피처(펀딩비) 교차 검증 후 진입 허용.
# Keywords: AND gate, hypothesis, funding rate, real-world confirmation

"""
진입 AND 게이트: 성경 레짐이 hypothesis일 때만 실물 피처(펀딩비/ETF) 충족 시 BUY/SELL 허용.
팩트체크 권장 [B] 구현. 2차 레짐 트리거 단독 사용 금지.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# 실험 플래그: AND_GATE_MODE=off | paper_trading | live(기본)
# off: AND 게이트 미적용(항상 허용). paper_trading: 검사만 수행·로그, 신호는 변경 안 함. live: 정책대로 적용.
ENV_AND_GATE_MODE = "AND_GATE_MODE"

logger = logging.getLogger(__name__)

# 프로젝트 루트: src/integration -> parent.parent.parent
BITCOIN_TRADING_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = BITCOIN_TRADING_ROOT.parent.parent
REGIME_DIR = WORKSPACE_ROOT / "data" / "regimes"
REGIME_FUSION_POLICY_PATH = REGIME_DIR / "regime_fusion_policy.json"
BTC6_SUPPLY_INDICATORS_PATH = BITCOIN_TRADING_ROOT / "data" / "btc6_supply" / "btc6_supply_indicators.json"

# 기본 임계값 (정책 파일 없을 때)
DEFAULT_FUNDING_RATE_MAX_FOR_LONG = 0.01   # 롱 허용: 펀딩비 이하 (과열 롱 아님)
DEFAULT_FUNDING_RATE_MIN_FOR_SHORT = -0.01  # 숏 허용: 펀딩비 이상 (과열 숏 아님)
MAX_AGE_SECONDS = 3600  # 1시간 이상 오래된 지표는 미사용


def _load_policy(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("entry_and_gate: policy 로드 실패 path=%s err=%s", path, e)
        return {}


def _get_latest_funding_rate_from_file(path: Path) -> Optional[float]:
    """btc6_supply_indicators.json에서 최신 funding_rate 1개 반환. 없거나 오래됐으면 None."""
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        rates = (data or {}).get("funding_rate") or []
        if not rates:
            return None
        # 최신이 마지막이라고 가정 (또는 timestamp 기준 정렬)
        latest = rates[-1] if isinstance(rates[-1], dict) else {"funding_rate": float(rates[-1])}
        return float(latest.get("funding_rate", 0.0))
    except Exception as e:
        logger.debug("entry_and_gate: funding rate 파일 읽기 실패 path=%s err=%s", path, e)
        return None


def _get_etf_net_flow_last_n_days(path: Path, n_days: int = 7) -> Optional[Tuple[float, int]]:
    """btc6_supply_indicators.json의 etf_flow에서 최근 n_days일 순유입/유출(USD) 합계. (합계, 일수) 또는 None."""
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        flows = (data or {}).get("etf_flow")
        if not flows or not isinstance(flows, list):
            return None
        by_date = sorted(
            [r for r in flows if r.get("etf_flow_usd") is not None],
            key=lambda x: x.get("date", ""),
            reverse=True,
        )
        total_usd = 0.0
        count = 0
        for r in by_date[:n_days]:
            v = r.get("etf_flow_usd")
            if v is not None:
                total_usd += float(v)
                count += 1
        return (total_usd, count) if count else None
    except Exception as e:
        logger.debug("entry_and_gate: etf_flow 읽기 실패 path=%s err=%s", path, e)
        return None


def check_entry_and_gate(
    signal: str,
    vector_4d: Dict[str, float],
    fusion_policy_path: Optional[Path] = None,
    supply_indicators_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    AND 게이트: 2차(성경) 레짐이 hypothesis일 때 실물 피처(펀딩비)로 교차 검증.
    BUY/SELL만 검사; HOLD는 그대로 통과.

    Returns:
        (allowed, reason)
        - allowed True: 진입 허용 (no_hypothesis / realworld_ok / and_gate_disabled)
        - allowed False: 진입 차단 (realworld_fail / realworld_funding_unavailable)
    """
    if signal not in ("BUY", "SELL"):
        return True, "hold_or_other"

    mode = os.environ.get(ENV_AND_GATE_MODE, "").strip().lower()
    if mode == "off":
        return True, "and_gate_mode_off"

    policy_path = fusion_policy_path or REGIME_FUSION_POLICY_PATH
    policy = _load_policy(policy_path)
    global_ = policy.get("global") or {}
    domain = (policy.get("domain_overrides") or {}).get("trading") or {}
    and_gate_enabled = global_.get("and_gate_enabled", domain.get("and_gate_enabled", True))
    if not and_gate_enabled:
        return True, "and_gate_disabled"

    try:
        from .btc6_regime_fusion_adapter import get_biblical_hypothesis_status
    except ImportError:
        try:
            from src.integration.btc6_regime_fusion_adapter import get_biblical_hypothesis_status
        except ImportError:
            logger.warning("entry_and_gate: get_biblical_hypothesis_status import 실패, AND 게이트 스킵")
            return True, "import_skip"

    biblical_is_hypothesis = get_biblical_hypothesis_status(vector_4d, None)
    if not biblical_is_hypothesis:
        return True, "no_hypothesis"

    # hypothesis일 때만 실물 피처 확인
    funding_max_long = float(
        global_.get("funding_rate_max_for_long")
        or domain.get("funding_rate_max_for_long")
        or DEFAULT_FUNDING_RATE_MAX_FOR_LONG
    )
    funding_min_short = float(
        global_.get("funding_rate_min_for_short")
        or domain.get("funding_rate_min_for_short")
        or DEFAULT_FUNDING_RATE_MIN_FOR_SHORT
    )

    supply_path = supply_indicators_path or BTC6_SUPPLY_INDICATORS_PATH
    funding_rate = _get_latest_funding_rate_from_file(supply_path)
    if funding_rate is None:
        logger.info("AND gate: 실물 피처(펀딩비) 없음 → 진입 차단 (hypothesis 상태)")
        return False, "realworld_funding_unavailable"

    and_use_etf = global_.get("and_use_etf_flow") or domain.get("and_use_etf_flow", False)
    etf_days = int(global_.get("etf_outflow_days") or domain.get("etf_outflow_days", 7))
    etf_outflow_required_sell = global_.get("etf_net_outflow_required_for_sell") is not False
    if "etf_net_outflow_required_for_sell" in domain:
        etf_outflow_required_sell = domain["etf_net_outflow_required_for_sell"]
    etf_min_flow_buy = global_.get("etf_min_flow_for_buy") or domain.get("etf_min_flow_for_buy")

    etf_flow_result: Optional[Tuple[float, int]] = None
    if and_use_etf:
        etf_flow_result = _get_etf_net_flow_last_n_days(supply_path, n_days=etf_days)
        if etf_flow_result is None:
            logger.debug("AND gate: and_use_etf_flow=True but etf_flow 없음 → 펀딩비만 사용")

    if signal == "BUY":
        if funding_rate > funding_max_long:
            logger.info(
                "AND gate: BUY 차단 (펀딩비 과열) funding_rate=%.4f > max_for_long=%.4f",
                funding_rate, funding_max_long,
            )
            return False, "realworld_fail"
        if and_use_etf and etf_flow_result is not None and etf_min_flow_buy is not None:
            etf_sum_usd, _ = etf_flow_result
            if etf_sum_usd < float(etf_min_flow_buy):
                logger.info(
                    "AND gate: BUY 차단 (ETF 순유입 부족) etf_sum_usd=%.0f < min=%.0f",
                    etf_sum_usd, float(etf_min_flow_buy),
                )
                return False, "realworld_fail"
        return True, "realworld_ok"

    # SELL
    if funding_rate < funding_min_short:
        logger.info(
            "AND gate: SELL 차단 (펀딩비 역과열) funding_rate=%.4f < min_for_short=%.4f",
            funding_rate, funding_min_short,
        )
        return False, "realworld_fail"
    if and_use_etf and etf_outflow_required_sell and etf_flow_result is not None:
        etf_sum_usd, etf_days_used = etf_flow_result
        if etf_sum_usd >= 0:
            logger.info(
                "AND gate: SELL 차단 (ETF 순유출 아님) etf_sum_usd=%.0f (최근 %d일)",
                etf_sum_usd, etf_days_used,
            )
            return False, "realworld_fail"
    return True, "realworld_ok"
