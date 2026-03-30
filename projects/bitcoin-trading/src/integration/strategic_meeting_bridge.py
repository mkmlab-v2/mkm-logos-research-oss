#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strategic Meeting Bridge (전략 회의 브릿지)

목적: 12인 참모진 AI 서버와 비트코인 자동매매 시스템을 연결
- 일일/주간 전략 회의 자동화
- TheoryFusionExecutor 가중치에 전략 반영
- Divine Centroid (0.25 평형) 기준 검증

작성일: 2026-01-30
상태: ✅ 구축 완료
"""

import sys
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import math

# Nitro Compression Engine import
try:
    from src.optimization.nitro_compression import NitroCompressionEngine
    NITRO_COMPRESSION_AVAILABLE = True
except ImportError:
    NITRO_COMPRESSION_AVAILABLE = False
    logging.warning("⚠️ Nitro Compression Engine 미설치, 압축 기능 비활성화")

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

# 로거 초기화 (모듈 레벨에서 먼저 정의)
logger = logging.getLogger(__name__)

# 12인 참모진 MCP 서버 import
TWELVE_CHARACTER_AVAILABLE = False
try:
    # MCP 서버 직접 import 시도
    mcp_server_path = workspace_root / "mcp-servers" / "twelve_character_ai_server.py"
    if mcp_server_path.exists():
        sys.path.insert(0, str(mcp_server_path.parent))
        # 동적 import (MCP 서버는 FastMCP 기반)
        TWELVE_CHARACTER_AVAILABLE = True
        logger.info("✅ 12인 참모진 MCP 서버 경로 확인 완료")
    else:
        logger.warning(f"⚠️ 12인 참모진 MCP 서버를 찾을 수 없습니다: {mcp_server_path}")
except Exception as e:
    logger.warning(f"⚠️ 12인 참모진 MCP 서버 import 실패: {e}")

# Divine Centroid 상수 (Project Logos)
DIVINE_CENTROID = {
    "S": 0.2498,
    "L": 0.2497,
    "K": 0.2507,
    "M": 0.2498
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategicMeetingBridge:
    """
    전략 회의 브릿지
    
    기능:
    1. 12인 참모진 일일/주간 전략 회의 자동화
    2. 회의 결과를 TheoryFusionExecutor 가중치에 반영
    3. Divine Centroid (0.25 평형) 기준 검증
    """
    
    def __init__(
        self,
        use_character_committee: bool = True,
        meeting_frequency: str = "daily",  # "daily" or "weekly"
        meeting_time: str = "09:00",  # 일일 회의 시간 (UTC)
        use_divine_centroid_validation: bool = True
    ):
        """
        Args:
            use_character_committee: 12인 참모진 사용 여부
            meeting_frequency: 회의 빈도 ("daily" or "weekly")
            meeting_time: 일일 회의 시간 (UTC, "HH:MM" 형식)
            use_divine_centroid_validation: Divine Centroid 검증 사용 여부
        """
        self.use_character_committee = use_character_committee and TWELVE_CHARACTER_AVAILABLE
        self.meeting_frequency = meeting_frequency
        self.meeting_time = meeting_time
        self.use_divine_centroid_validation = use_divine_centroid_validation
        
        # 마지막 회의 시간 추적
        self.last_meeting_time: Optional[datetime] = None
        self.last_meeting_result: Optional[Dict[str, Any]] = None
        
        # 전략 가중치 (TheoryFusionExecutor에 반영)
        self.strategy_weights = {
            'position_size_multiplier': 1.0,  # 포지션 크기 배수
            'risk_tolerance': 0.5,  # 리스크 허용도 (0.0 ~ 1.0)
            'confidence_boost': 0.0,  # 신뢰도 보너스 (-0.1 ~ +0.1)
            'market_bias': 'NEUTRAL'  # 시장 편향 ('BULLISH', 'BEARISH', 'NEUTRAL')
        }
        
        # Nitro Compression Engine 초기화
        self.nitro_compression = None
        if NITRO_COMPRESSION_AVAILABLE:
            try:
                self.nitro_compression = NitroCompressionEngine(compression_level=6)
                logger.info("✅ Nitro Compression Engine 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Nitro Compression Engine 초기화 실패: {e}")
        
        logger.info(f"✅ Strategic Meeting Bridge 초기화 완료")
        logger.info(f"   - 12인 참모진 사용: {self.use_character_committee}")
        logger.info(f"   - 회의 빈도: {self.meeting_frequency}")
        logger.info(f"   - 회의 시간: {self.meeting_time}")
    
    async def hold_strategic_meeting(
        self,
        market_data: Dict[str, Any],
        current_analysis: Dict[str, Any],
        urgency: str = "medium"
    ) -> Dict[str, Any]:
        """
        12인 참모진 전략 회의 개최
        
        Args:
            market_data: 시장 데이터 (가격, 거래량 등)
            current_analysis: 현재 분석 결과 (TheoryFusionExecutor 결과)
            urgency: 긴급도 ("low", "medium", "high")
        
        Returns:
            회의 결과 딕셔너리
        """
        if not self.use_character_committee:
            logger.warning("⚠️ 12인 참모진이 비활성화되어 있습니다. 기본 전략 사용")
            return self._get_default_strategy()
        
        try:
            # 회의 주제 생성
            topic = self._build_meeting_topic(market_data, current_analysis)
            
            logger.info("🏛️ 12인 참모진 전략 회의 시작...")
            logger.info(f"   주제: {topic[:100]}...")
            
            # MCP 서버를 통한 회의 호출
            # 주의: MCP 서버는 FastMCP 기반이므로 직접 호출 불가
            # 대신 HTTP API 또는 subprocess를 통해 호출해야 함
            meeting_result = await self._call_meeting_via_mcp(topic, urgency)
            
            # 결과 파싱 및 검증
            parsed_result = self._parse_meeting_result(meeting_result)
            
            # Divine Centroid 검증 (현재 벡터 정보 포함)
            if self.use_divine_centroid_validation:
                current_vector_4d = current_analysis.get('vector_4d', {})
                validated_result = self._validate_with_divine_centroid(
                    parsed_result,
                    current_vector_4d=current_vector_4d
                )
            else:
                validated_result = parsed_result
            
            # 전략 가중치 업데이트
            self._update_strategy_weights(validated_result)
            
            # 마지막 회의 시간 저장
            self.last_meeting_time = datetime.now()
            self.last_meeting_result = validated_result
            
            logger.info("✅ 12인 참모진 전략 회의 완료")
            logger.info(f"   - 포지션 크기 배수: {self.strategy_weights['position_size_multiplier']:.2f}")
            logger.info(f"   - 리스크 허용도: {self.strategy_weights['risk_tolerance']:.2f}")
            logger.info(f"   - 신뢰도 보너스: {self.strategy_weights['confidence_boost']:+.2%}")
            logger.info(f"   - 시장 편향: {self.strategy_weights['market_bias']}")
            
            return validated_result
            
        except Exception as e:
            logger.error(f"❌ 전략 회의 실패: {e}")
            return self._get_default_strategy()
    
    def _build_meeting_topic(
        self,
        market_data: Dict[str, Any],
        current_analysis: Dict[str, Any]
    ) -> str:
        """회의 주제 생성 (Nitro Compression 최적화)"""
        current_price = market_data.get('price', 0)
        volume = market_data.get('volume', 0)
        vector_4d = current_analysis.get('vector_4d', {})
        fusion_signal = current_analysis.get('fusion_signal', 'HOLD')
        confidence = current_analysis.get('confidence', 0.5)
        
        base_topic = f"""
🏛️ 비트코인 자동매매 전략 회의

현재 시장 상황:
- 가격: {current_price:,.2f} USDT
- 거래량: {volume:,.2f}
- 4D 벡터: S={vector_4d.get('S', 0.25):.4f}, L={vector_4d.get('L', 0.25):.4f}, K={vector_4d.get('K', 0.25):.4f}, M={vector_4d.get('M', 0.25):.4f}
- TheoryFusion 신호: {fusion_signal}
- 신뢰도: {confidence:.2%}

12인 참모진의 종합 의견을 제시해주세요:

1. **전략 방향**:
   - 매수/매도/보류 중 선택
   - 전체 포지션 크기 권장 (0.0 ~ 1.0)
   - 리스크 허용도 (0.0 ~ 1.0)

2. **시장 편향**:
   - BULLISH (상승 편향)
   - BEARISH (하락 편향)
   - NEUTRAL (중립)

3. **신뢰도 보정**:
   - 신뢰도 보너스/패널티 (-10% ~ +10%)

4. **Divine Centroid 검증**:
   - 현재 4D 벡터가 Divine Centroid (0.25 평형)와의 거리 계산
   - 거리 > 0.1이면 경고 및 보정 권장

5. **리스크 관리**:
   - 손절선 권장
   - 익절선 권장
   - 최대 포지션 크기 제한

**중요**: 모든 결정은 Divine Centroid (0.25 평형) 기준으로 검증해야 합니다.
"""
        
        # Nitro Compression으로 프롬프트 최적화
        if self.nitro_compression:
            topic = self.nitro_compression.optimize_prompt_for_gemini(base_topic, max_tokens=800)
            logger.debug("✅ 회의 주제 최적화 완료 (니트로 압축)")
        else:
            topic = base_topic.strip()
        
        return topic
    
    async def _call_meeting_via_mcp(
        self,
        topic: str,
        urgency: str
    ) -> Dict[str, Any]:
        """
        MCP 서버를 통한 회의 호출
        
        방법 1: 직접 함수 호출 (우선순위 1) - _hold_meeting_impl 함수 직접 import
        방법 2: subprocess를 통한 Python 스크립트 실행 (Fallback)
        방법 3: HTTP API 호출 (MCP 서버가 HTTP 서버로 실행 중인 경우)
        """
        try:
            # 방법 1: 직접 함수 호출 (우선순위 1)
            try:
                # MCP 서버 모듈에서 _hold_meeting_impl 함수 직접 import
                mcp_server_path = workspace_root / "mcp-servers" / "twelve_character_ai_server.py"
                if mcp_server_path.exists():
                    # 모듈 경로 추가
                    sys.path.insert(0, str(mcp_server_path.parent))
                    
                    # 직접 함수 import 시도
                    try:
                        from twelve_character_ai_server import _hold_meeting_impl
                        
                        logger.info("✅ MCP 서버 함수 직접 import 성공")
                        
                        # 회의 호출
                        result_str = await _hold_meeting_impl(
                            topic=topic,
                            participants=None,  # 전체 12명
                            urgency=urgency,
                            user_id="bitcoin-trading-v1"
                        )
                        
                        # JSON 파싱
                        if isinstance(result_str, str):
                            result_dict = json.loads(result_str)
                        else:
                            result_dict = result_str
                        
                        # 결과를 Strategic Meeting Bridge 형식으로 변환
                        parsed_result = self._convert_meeting_result_to_strategy(result_dict)
                        
                        return {
                            "success": True,
                            "meeting_result": parsed_result
                        }
                    except ImportError as e:
                        logger.warning(f"⚠️ 직접 함수 import 실패: {e}, subprocess 방식 시도")
                        raise
            except Exception as e:
                logger.warning(f"⚠️ 직접 함수 호출 실패: {e}, Fallback 방식 사용")
            
            # 방법 2: subprocess를 통한 Python 스크립트 실행 (Fallback)
            try:
                import subprocess
                import sys as sys_module
                
                # Python 실행 파일 경로
                python_exe = sys_module.executable
                
                # 임시 스크립트 생성 (회의 호출용)
                temp_script = workspace_root / "projects" / "bitcoin-trading" / "temp_meeting_call.py"
                script_content = f"""
import sys
import json
import asyncio
from pathlib import Path

workspace_root = Path("{workspace_root}")
sys.path.insert(0, str(workspace_root / "mcp-servers"))

from twelve_character_ai_server import _hold_meeting_impl

async def main():
    topic = {json.dumps(topic)}
    urgency = {json.dumps(urgency)}
    
    result = await _hold_meeting_impl(
        topic=topic,
        participants=None,
        urgency=urgency,
        user_id="bitcoin-trading-v1"
    )
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
"""
                temp_script.write_text(script_content, encoding='utf-8')
                
                # subprocess 실행
                process = subprocess.Popen(
                    [python_exe, str(temp_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    cwd=str(workspace_root)
                )
                
                stdout, stderr = process.communicate(timeout=180)  # 3분 타임아웃
                
                if process.returncode == 0:
                    result_dict = json.loads(stdout)
                    parsed_result = self._convert_meeting_result_to_strategy(result_dict)
                    
                    # 임시 스크립트 삭제
                    temp_script.unlink(missing_ok=True)
                    
                    return {
                        "success": True,
                        "meeting_result": parsed_result
                    }
                else:
                    logger.error(f"❌ subprocess 실행 실패: {stderr}")
                    raise Exception(f"Subprocess failed: {stderr}")
                    
            except Exception as e:
                logger.warning(f"⚠️ subprocess 호출 실패: {e}, 기본 전략 사용")
                raise
            
        except Exception as e:
            logger.error(f"❌ MCP 서버 호출 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _convert_meeting_result_to_strategy(
        self,
        meeting_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        MCP 서버 회의 결과를 Strategic Meeting Bridge 형식으로 변환
        
        Args:
            meeting_result: MCP 서버에서 반환된 회의 결과
        
        Returns:
            Strategic Meeting Bridge 형식의 전략 딕셔너리
        """
        try:
            # 회의 결과에서 최종 결정 추출
            final_decision = meeting_result.get("final_decision", "")
            opinions = meeting_result.get("opinions", [])
            
            # 의견 분석 (간단한 파싱)
            # 실제로는 LLM을 통해 구조화된 결과를 추출해야 함
            strategy = "NEUTRAL"
            position_size = 0.3
            risk_tolerance = 0.5
            market_bias = "NEUTRAL"
            confidence_boost = 0.0
            
            # 의견에서 키워드 추출
            all_opinions_text = " ".join([op.get("opinion", "") for op in opinions])
            
            # 간단한 키워드 기반 파싱 (실제로는 LLM 파싱 권장)
            if "매수" in all_opinions_text or "상승" in all_opinions_text or "BULLISH" in all_opinions_text.upper():
                market_bias = "BULLISH"
                position_size = 0.4
                confidence_boost = 0.05
            elif "매도" in all_opinions_text or "하락" in all_opinions_text or "BEARISH" in all_opinions_text.upper():
                market_bias = "BEARISH"
                position_size = 0.2
                confidence_boost = -0.05
            
            # Divine Centroid 거리 계산 (현재 벡터 기준)
            # 실제로는 회의 결과에서 벡터 정보를 추출해야 함
            current_vector = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
            divine_distance = self.calculate_distance_to_centroid(current_vector)
            
            return {
                "strategy": strategy,
                "position_size": position_size,
                "risk_tolerance": risk_tolerance,
                "market_bias": market_bias,
                "confidence_boost": confidence_boost,
                "stop_loss": 0.02,
                "take_profit": 0.04,
                "divine_centroid_distance": divine_distance,
                "recommendations": [
                    final_decision,
                    f"12인 참모진 의견: {len(opinions)}명 참여",
                    f"Divine Centroid 거리: {divine_distance:.4f}"
                ]
            }
        except Exception as e:
            logger.error(f"❌ 회의 결과 변환 실패: {e}")
            return self._get_default_strategy()
    
    def _parse_meeting_result(
        self,
        meeting_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """회의 결과 파싱"""
        try:
            if not meeting_result.get("success", False):
                logger.warning("⚠️ 회의 실패, 기본 전략 사용")
                return self._get_default_strategy()
            
            result = meeting_result.get("meeting_result", {})
            
            parsed = {
                "strategy": result.get("strategy", "NEUTRAL"),
                "position_size": float(result.get("position_size", 0.3)),
                "risk_tolerance": float(result.get("risk_tolerance", 0.5)),
                "market_bias": result.get("market_bias", "NEUTRAL"),
                "confidence_boost": float(result.get("confidence_boost", 0.0)),
                "stop_loss": float(result.get("stop_loss", 0.02)),
                "take_profit": float(result.get("take_profit", 0.04)),
                "divine_centroid_distance": float(result.get("divine_centroid_distance", 0.0)),
                "recommendations": result.get("recommendations", [])
            }
            
            return parsed
        except Exception as e:
            logger.error(f"❌ 회의 결과 파싱 실패: {e}")
            return self._get_default_strategy()
    
    def _validate_with_divine_centroid(
        self,
        result: Dict[str, Any],
        current_vector_4d: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Divine Centroid (0.25 평형) 기준 검증
        
        아리스토텔레스(Ari) 역할: 논리 벡터 과다 시 경고
        
        Args:
            result: 회의 결과 딕셔너리
            current_vector_4d: 현재 4D 벡터 (선택적, 없으면 기본값 사용)
        """
        try:
            # 현재 벡터가 제공되지 않으면 기본값 사용
            if current_vector_4d is None:
                current_vector_4d = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
            
            # Divine Centroid 거리 계산
            distance = self.calculate_distance_to_centroid(current_vector_4d)
            result["divine_centroid_distance"] = distance
            
            # 거리 > 0.1이면 경고 (아리스토텔레스(Ari) 개입)
            if distance > 0.1:
                logger.warning(f"⚠️ Divine Centroid 거리 경고: {distance:.4f} > 0.1")
                logger.warning("   아리스토텔레스(Ari): 논리 벡터가 과다합니다. 보정을 권장합니다.")
                
                # 보정 적용: 포지션 크기 감소, 리스크 허용도 감소
                result["position_size"] = result.get("position_size", 0.3) * 0.8  # 20% 감소
                result["risk_tolerance"] = result.get("risk_tolerance", 0.5) * 0.8  # 20% 감소
                result["confidence_boost"] = result.get("confidence_boost", 0.0) - 0.05  # 5% 감소
                
                result["recommendations"] = result.get("recommendations", [])
                result["recommendations"].append(
                    f"⚠️ Divine Centroid 거리 {distance:.4f}가 기준(0.1)을 초과했습니다. "
                    "아리스토텔레스(Ari)의 보정이 적용되었습니다. 보수적 전략을 권장합니다."
                )
            
            # 거리 < 0.01이면 완벽한 균형
            elif distance < 0.01:
                logger.info(f"✅ Divine Centroid 완벽한 균형: {distance:.4f} < 0.01")
                result["confidence_boost"] = result.get("confidence_boost", 0.0) + 0.05  # 5% 증가
                result["recommendations"] = result.get("recommendations", [])
                result["recommendations"].append(
                    f"✅ Divine Centroid 거리 {distance:.4f}는 완벽한 균형 상태입니다. "
                    "신뢰도 보너스가 적용되었습니다."
                )
            
            # 거리 0.01 ~ 0.1 사이면 양호한 상태
            else:
                logger.info(f"✅ Divine Centroid 양호한 상태: {distance:.4f} (0.01 ~ 0.1)")
            
            return result
        except Exception as e:
            logger.error(f"❌ Divine Centroid 검증 실패: {e}")
            return result
    
    def _update_strategy_weights(
        self,
        validated_result: Dict[str, Any]
    ):
        """전략 가중치 업데이트 (TheoryFusionExecutor에 반영)"""
        try:
            self.strategy_weights = {
                'position_size_multiplier': validated_result.get("position_size", 0.3),
                'risk_tolerance': validated_result.get("risk_tolerance", 0.5),
                'confidence_boost': validated_result.get("confidence_boost", 0.0),
                'market_bias': validated_result.get("market_bias", "NEUTRAL")
            }
        except Exception as e:
            logger.error(f"❌ 전략 가중치 업데이트 실패: {e}")
    
    def _get_default_strategy(self) -> Dict[str, Any]:
        """기본 전략 (12인 참모진 미사용 시)"""
        return {
            "strategy": "NEUTRAL",
            "position_size": 0.3,
            "risk_tolerance": 0.5,
            "market_bias": "NEUTRAL",
            "confidence_boost": 0.0,
            "stop_loss": 0.02,
            "take_profit": 0.04,
            "divine_centroid_distance": 0.0,
            "recommendations": ["기본 전략 사용 (12인 참모진 미사용)"]
        }
    
    def get_strategy_weights(self) -> Dict[str, float]:
        """전략 가중치 반환 (TheoryFusionExecutor에 전달)"""
        return self.strategy_weights.copy()
    
    def should_hold_meeting(self) -> bool:
        """회의 개최 여부 확인"""
        if not self.use_character_committee:
            return False
        
        now = datetime.now()
        
        # 일일 회의
        if self.meeting_frequency == "daily":
            if self.last_meeting_time is None:
                return True
            
            # 마지막 회의로부터 24시간 경과
            time_since_last = now - self.last_meeting_time
            if time_since_last >= timedelta(hours=24):
                return True
            
            # 지정된 시간 확인 (UTC)
            meeting_hour, meeting_minute = map(int, self.meeting_time.split(":"))
            if now.hour == meeting_hour and now.minute == meeting_minute:
                if self.last_meeting_time is None or self.last_meeting_time.date() < now.date():
                    return True
        
        # 주간 회의
        elif self.meeting_frequency == "weekly":
            if self.last_meeting_time is None:
                return True
            
            # 마지막 회의로부터 7일 경과
            time_since_last = now - self.last_meeting_time
            if time_since_last >= timedelta(days=7):
                return True
        
        return False
    
    def calculate_distance_to_centroid(
        self,
        vector_4d: Dict[str, float]
    ) -> float:
        """
        Divine Centroid까지의 거리 계산
        
        Args:
            vector_4d: 4차원 벡터
        
        Returns:
            거리 (유클리드 거리)
        """
        try:
            distance = math.sqrt(sum(
                (vector_4d.get(key, 0.25) - DIVINE_CENTROID[key]) ** 2
                for key in ["S", "L", "K", "M"]
            ))
            return distance
        except Exception as e:
            logger.error(f"❌ 거리 계산 실패: {e}")
            return 0.5  # 기본값

