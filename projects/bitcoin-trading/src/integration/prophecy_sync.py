#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
예언 리포트 동기화 모듈
- Divine Distance 기반 자동 비중 조절
- PGAE: 14B용 예언 컨텍스트 팩 (load_prophecy_context)
- 바이브 코딩: 핵심만 간결하게
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# WORKSPACE_ROOT 계산: projects/bitcoin-trading/src/integration -> 5단계 상위 (C:\workspace)
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent.parent
# 예언 리포트 경로: 루트 docs/prophecy/2026_Real_Prophecy_Report.md
PROPHECY_REPORT_PATH = WORKSPACE_ROOT / "docs" / "prophecy" / "2026_Real_Prophecy_Report.md"
PROPHECY_DOCS_PATH = WORKSPACE_ROOT / "docs" / "prophecy"
# 4d_native_config Fallback 경로 (Restorer 출력)
ADAPTER_CONFIG_DIR = WORKSPACE_ROOT / "data" / "adapters"


def _load_distance_from_adapter_configs() -> Optional[float]:
    """
    Fallback: 4d_native_config_*.json에서 divine_distance 추출.
    .md/예언 리포트가 없을 때 Code Pack Restorer 출력을 직접 참조.
    """
    try:
        configs = list(ADAPTER_CONFIG_DIR.glob("4d_native_config_*.json"))
        if not configs:
            return None
        # 수정 시간 기준 최신순, divine_distance > 0인 첫 config 사용
        for path in sorted(configs, key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                d = data.get("divine_distance")
                if d is not None and float(d) > 0:
                    logger.info(f"📊 4d_native_config Fallback: {path.name} → divine_distance={d:.4f}")
                    return float(d)
            except Exception:
                continue
        return None
    except Exception as e:
        logger.debug(f"4d_native_config Fallback 실패: {e}")
        return None


def load_prophecy_distance() -> Optional[float]:
    """예언 리포트에서 Divine Distance 추출. 없으면 4d_native_config Fallback."""
    try:
        if PROPHECY_REPORT_PATH.exists():
            content = PROPHECY_REPORT_PATH.read_text(encoding="utf-8")
            patterns = [
                r"Divine Distance[:\s]+([\d.]+)",
                r"Distance[:\s]+([\d.]+)",
                r"종합 거리[:\s]+([\d.]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    distance = float(match.group(1))
                    logger.info(f"📊 예언 리포트 Divine Distance: {distance:.4f}")
                    return distance

        # Fallback: 4d_native_config_*.json (Code Pack Restorer 출력)
        fallback = _load_distance_from_adapter_configs()
        if fallback is not None:
            return fallback

        if not PROPHECY_REPORT_PATH.exists():
            logger.warning(f"⚠️ 예언 리포트 없음: {PROPHECY_REPORT_PATH}")
        else:
            logger.warning("⚠️ 예언 리포트에서 Distance 추출 실패")
        return None
    except Exception as e:
        logger.warning(f"⚠️ 예언 리포트 로드 실패: {e}")
        return _load_distance_from_adapter_configs()

def load_prophecy_context() -> Dict[str, Any]:
    """
    PGAE: 14B용 예언 컨텍스트 팩.
    Divine Distance, crisis_level, vector_4d, predicted_events, today_summary 반환.
    """
    out: Dict[str, Any] = {
        "divine_distance": 0.0,
        "crisis_level": "UNKNOWN",
        "vector_4d": {},
        "predicted_events": [],
        "prophecy_direction": "NEUTRAL",
        "today_summary": "",
    }
    try:
        out["divine_distance"] = load_prophecy_distance()
    except Exception:
        pass

    # final_prophecy_apocalypse_2026_*.json (최신 파일)
    apoc_dir = PROPHECY_DOCS_PATH
    if not apoc_dir.exists():
        return out
    apoc_files = sorted(apoc_dir.glob("final_prophecy_apocalypse_2026_*.json"), reverse=True)
    if not apoc_files:
        return out

    try:
        with open(apoc_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("prophecy_context: apocalypse load failed: %s", e)
        return out

    p26 = data.get("prophecy_2026") or {}
    out["crisis_level"] = p26.get("crisis_level") or "UNKNOWN"
    out["vector_4d"] = p26.get("vector_4d") or {}
    out["predicted_events"] = p26.get("predicted_events") or []

    # prophecy_direction: 예언 기반 방향성 (14B 참고용)
    crisis = out["crisis_level"].upper()
    events = [e.lower() for e in out["predicted_events"]]
    if crisis in ("CRISIS", "COLLAPSE") or any(
        x in " ".join(events) for x in ("붕괴", "급락", "인플레이션")
    ):
        out["prophecy_direction"] = "CAUTION_DOWN"
    elif crisis == "STABLE":
        out["prophecy_direction"] = "NEUTRAL"
    else:
        out["prophecy_direction"] = "CAUTION_DOWN"

    # today_summary: 짧은 설명 (14B 프롬프트용)
    desc = p26.get("description") or ""
    btc = (data.get("athena_proposal") or {}).get("bitcoin_strategy") or {}
    strategy = btc.get("strategy") or ""
    out["today_summary"] = f"{desc[:100]}{' ' + strategy[:80] if strategy else ''}".strip()

    return out


def adjust_weights_by_prophecy(
    base_weights: Dict[str, float],
    distance: float
) -> Dict[str, float]:
    """
    Divine Distance 기반 가중치 조정
    
    - distance >= 0.3: 방어적 (Bayesian, MCMC 가중치 증가)
    - distance < 0.2: 공격적 (HMM, RL 가중치 증가)
    - 0.2 <= distance < 0.3: 균형 (기본 가중치 유지)
    """
    adjusted = base_weights.copy()
    
    if distance >= 0.3:
        # 위기 모드: 방어적 전략
        factor = min((distance - 0.3) / 0.1, 1.0)  # 0.3~0.4 → 0.0~1.0
        if "bayesian_update" in adjusted:
            adjusted["bayesian_update"] *= (1.0 + factor * 0.3)
        if "mcmc" in adjusted:
            adjusted["mcmc"] *= (1.0 + factor * 0.2)
        if "hmm" in adjusted:
            adjusted["hmm"] *= (1.0 - factor * 0.15)
        if "reinforcement_learning" in adjusted:
            adjusted["reinforcement_learning"] *= (1.0 - factor * 0.15)
        logger.info(f"🛡️ 위기 모드 (distance={distance:.4f}): 방어적 전략 활성화")
    elif distance < 0.2:
        # 안정 모드: 공격적 전략
        factor = (0.2 - distance) / 0.2  # 0.0~0.2 → 1.0~0.0
        if "hmm" in adjusted:
            adjusted["hmm"] *= (1.0 + factor * 0.2)
        if "reinforcement_learning" in adjusted:
            adjusted["reinforcement_learning"] *= (1.0 + factor * 0.15)
        if "bayesian_update" in adjusted:
            adjusted["bayesian_update"] *= (1.0 - factor * 0.1)
        logger.info(f"🚀 안정 모드 (distance={distance:.4f}): 공격적 전략 활성화")
    else:
        # 균형 모드: 기본 가중치 유지
        logger.info(f"⚖️ 균형 모드 (distance={distance:.4f}): 기본 전략 유지")
    
    return adjusted

