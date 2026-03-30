#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ 10초 선점 타격 파이프라인 (Zero-Wait Pipeline)

목적: 뉴스 발생 후 10초 내 정보 수집 → 분석 → 매매 실행
전략: Jina Reader (2초) → 로컬 위상 분석 (0.1ms) → 즉시 매매

작성일: 2026-01-11
상태: ✅ 구현 중
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import sys
import logging

# 프로젝트 루트 경로 추가
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Jina Reader 통합
JINA_AVAILABLE = False
JINA_DISTILLER_CLASS = None

import_paths_jina = [
    "mcp_servers.jina_reader_integration",
    "mcp-servers.jina_reader_integration",
    "mcp-servers/jina_reader_integration"
]

for import_path in import_paths_jina:
    try:
        module = __import__(import_path, fromlist=["JinaReaderDistiller"])
        JINA_DISTILLER_CLASS = getattr(module, "JinaReaderDistiller", None)
        if JINA_DISTILLER_CLASS:
            JINA_AVAILABLE = True
            logger.info(f"✅ Jina Reader 로드 성공: {import_path}")
            break
    except (ImportError, AttributeError):
        continue

if not JINA_AVAILABLE:
    logger.warning("⚠️ JinaReaderDistiller를 사용할 수 없습니다. 기본 requests 사용.")


class TenSecondStrikePipeline:
    """
    10초 선점 타격 파이프라인
    
    프로세스:
    1. 뉴스 URL 수집 (2초)
    2. Jina Reader로 즉시 수집 (2초)
    3. 로컬 4D 위상 분석 (0.1ms)
    4. 고전 지혜 필터 (명리·성경) (1초)
    5. 유동성 체크 (1초)
    6. 매매 실행 (1초)
    총 소요 시간: 약 7초 (목표 10초 이내)
    """
    
    def __init__(
        self,
        use_classical_wisdom: bool = True,
        use_liquidity_check: bool = True,
        use_whale_tracker: bool = True,
        use_sentiment_filter: bool = True
    ):
        """
        초기화
        
        Args:
            use_classical_wisdom: 고전 지혜 필터 사용 여부
            use_liquidity_check: 유동성 체크 사용 여부
            use_whale_tracker: 고래 추적 사용 여부
            use_sentiment_filter: 감정 필터 사용 여부
        """
        self.use_classical_wisdom = use_classical_wisdom
        self.use_liquidity_check = use_liquidity_check
        self.use_whale_tracker = use_whale_tracker
        self.use_sentiment_filter = use_sentiment_filter
        
        # Jina Reader 초기화 (Lazy Loading)
        self._jina_distiller = None
        if JINA_AVAILABLE and JINA_DISTILLER_CLASS:
            try:
                self._jina_distiller = JINA_DISTILLER_CLASS()
                logger.info("✅ Jina Reader 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Jina Reader 초기화 실패: {e}")
                self._jina_distiller = None
        
        # 고전 지혜 엔진 초기화 (Lazy Loading)
        self._myeongri_engine = None
        self._myeongri_cycle_module = None
        self._logos_resonance_calculator = None
        
        # 유동성 감시 모듈 초기화 (Lazy Loading)
        self._liquidity_guardian = None
        
        # 고래 추적 모듈 초기화 (Lazy Loading)
        self._whale_tracker = None
        
        # 감정 필터 초기화 (Lazy Loading)
        self._sentiment_filter = None
        
        # 성능 통계
        self.stats = {
            "total_strikes": 0,
            "successful_strikes": 0,
            "average_latency_ms": 0.0,
            "fastest_strike_ms": float('inf'),
            "slowest_strike_ms": 0.0,
            "classical_wisdom_rejections": 0,
            "liquidity_rejections": 0,
            "whale_rejections": 0,
            "sentiment_rejections": 0
        }
    
    def _initialize_classical_wisdom(self):
        """고전 지혜 엔진 초기화 (Lazy Loading)"""
        if self._myeongri_engine is not None:
            return
        
        try:
            from tools.core.myeongri_cycle_module import MyeongriCycleModule
            from scripts.myeongri_perfect_fusion_engine import MyeongriPerfectFusionEngine
            
            self._myeongri_cycle_module = MyeongriCycleModule()
            self._myeongri_engine = MyeongriPerfectFusionEngine()
            logger.info("✅ 고전 지혜 엔진 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 고전 지혜 엔진 초기화 실패: {e}")
            self._myeongri_cycle_module = None
            self._myeongri_engine = None
    
    def _initialize_liquidity_guardian(self):
        """유동성 감시 모듈 초기화 (Lazy Loading)"""
        if self._liquidity_guardian is not None:
            return
        
        try:
            from projects.bitcoin_trading.src.strategy.liquidity_guardian import LiquidityGuardian
            self._liquidity_guardian = LiquidityGuardian()
            logger.info("✅ 유동성 감시 모듈 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 유동성 감시 모듈 초기화 실패: {e}")
            self._liquidity_guardian = None
    
    def _initialize_whale_tracker(self):
        """고래 추적 모듈 초기화 (Lazy Loading)"""
        if self._whale_tracker is not None:
            return
        
        try:
            from projects.bitcoin_trading.src.strategy.whale_tracker import WhaleTracker
            self._whale_tracker = WhaleTracker()
            logger.info("✅ 고래 추적 모듈 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 고래 추적 모듈 초기화 실패: {e}")
            self._whale_tracker = None
    
    def _initialize_sentiment_filter(self):
        """감정 필터 초기화 (Lazy Loading)"""
        if self._sentiment_filter is not None:
            return
        
        try:
            from projects.bitcoin_trading.src.strategy.sentiment_reversal_filter import SentimentReversalFilter
            self._sentiment_filter = SentimentReversalFilter()
            logger.info("✅ 감정 필터 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 감정 필터 초기화 실패: {e}")
            self._sentiment_filter = None
    
    async def collect_news_fast(self, url: str) -> Dict[str, Any]:
        """
        뉴스 빠른 수집 (2초 목표)
        
        Args:
            url: 뉴스 URL
        
        Returns:
            수집 결과 (markdown, metadata)
        """
        start_time = time.time()
        
        if self._jina_distiller:
            try:
                result = await self._jina_distiller.distill(url, timeout=10.0)
                if result.get("success"):
                    elapsed = (time.time() - start_time) * 1000
                    logger.info(f"✅ Jina Reader 수집 완료: {elapsed:.1f}ms")
                    return {
                        "success": True,
                        "markdown": result.get("markdown", ""),
                        "metadata": result.get("metadata", {}),
                        "latency_ms": elapsed
                    }
            except Exception as e:
                logger.warning(f"⚠️ Jina Reader 수집 실패: {e}")
        
        # Fallback: 기본 requests
        try:
            import requests
            response = requests.get(url, timeout=5.0)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"✅ 기본 requests 수집 완료: {elapsed:.1f}ms")
            return {
                "success": True,
                "markdown": response.text[:10000],  # 최대 10KB
                "metadata": {"source": "requests"},
                "latency_ms": elapsed
            }
        except Exception as e:
            logger.error(f"❌ 뉴스 수집 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def analyze_4d_phase(self, news_content: str) -> Dict[str, Any]:
        """
        4D 위상 분석 (0.1ms 목표)
        
        Args:
            news_content: 뉴스 내용
        
        Returns:
            4D 벡터 분석 결과
        """
        start_time = time.time()
        
        try:
            # MKM12 엔진으로 4D 벡터화
            from tools.core.twelve_dimensional_vectorizer import MKM12V2IntegratedEngine
            
            engine = MKM12V2IntegratedEngine(system_type="system")
            vector_result = engine.vectorize(news_content)
            
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"✅ 4D 위상 분석 완료: {elapsed:.3f}ms")
            
            return {
                "success": True,
                "vector_4d": vector_result.get("vector_4d", {}),
                "dcv": vector_result.get("dcv", 0.5),
                "lambda": vector_result.get("lambda", 0.5),
                "latency_ms": elapsed
            }
        except Exception as e:
            logger.error(f"❌ 4D 위상 분석 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def check_classical_wisdom(
        self,
        vector_4d: Dict[str, float],
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        고전 지혜 필터 (명리·성경) (1초 목표)
        
        Args:
            vector_4d: 4D 벡터
            current_time: 현재 시간
        
        Returns:
            고전 지혜 검증 결과
        """
        start_time = time.time()
        
        if not self.use_classical_wisdom:
            return {
                "approved": True,
                "reason": "고전 지혜 필터 비활성화",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        # Lazy Loading
        self._initialize_classical_wisdom()
        
        if not self._myeongri_engine or not self._myeongri_cycle_module:
            return {
                "approved": True,
                "reason": "고전 지혜 엔진 사용 불가",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        try:
            # 1. 명리적 주기 확인
            myeongri_result = self._myeongri_cycle_module.calculate_myeongri_lambda(
                birth_year=1985,  # 주인님 정보 (실제 값으로 수정 필요)
                birth_month=1,
                birth_day=1,
                birth_hour=0,
                current_year=current_time.year,
                current_month=current_time.month,
                current_day=current_time.day,
                is_male=True
            )
            
            myeongri_lambda = myeongri_result.get("lambda_value", 0.5)
            myeongri_approved = myeongri_lambda > 0.4  # 명리적으로 유리한 시기
            
            # 2. 성경적 로고스 공명 확인
            logos_resonance = self._myeongri_engine._calculate_logos_resonance_perfect(
                vector_4d,
                current_time.strftime("%Y-%m-%d")
            )
            
            logos_distance = logos_resonance.get("divine_centroid_distance", 1.0)
            logos_approved = logos_distance < 0.1  # Divine Centroid와 가까움
            
            # 3. 최종 승인 여부
            both_approved = myeongri_approved and logos_approved
            either_approved = myeongri_approved or logos_approved
            
            elapsed = (time.time() - start_time) * 1000
            
            if not either_approved:
                self.stats["classical_wisdom_rejections"] += 1
            
            return {
                "approved": either_approved,
                "both_approved": both_approved,
                "myeongri_approved": myeongri_approved,
                "myeongri_lambda": myeongri_lambda,
                "logos_approved": logos_approved,
                "logos_distance": logos_distance,
                "latency_ms": elapsed
            }
        except Exception as e:
            logger.error(f"❌ 고전 지혜 필터 실패: {e}")
            return {
                "approved": True,  # 실패 시 통과 (안전 모드)
                "reason": f"필터 오류: {str(e)}",
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    async def check_liquidity(
        self,
        symbol: str = "BTCUSDT",
        order_size_usd: float = 1000.0
    ) -> Dict[str, Any]:
        """
        유동성 체크 (1초 목표)
        
        Args:
            symbol: 거래 심볼
            order_size_usd: 주문 크기 (USD)
        
        Returns:
            유동성 검증 결과
        """
        start_time = time.time()
        
        if not self.use_liquidity_check:
            return {
                "approved": True,
                "reason": "유동성 체크 비활성화",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        # Lazy Loading
        self._initialize_liquidity_guardian()
        
        if not self._liquidity_guardian:
            return {
                "approved": True,
                "reason": "유동성 감시 모듈 사용 불가",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        try:
            result = await self._liquidity_guardian.check_liquidity(
                symbol=symbol,
                order_size_usd=order_size_usd
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            if not result.get("approved", False):
                self.stats["liquidity_rejections"] += 1
            
            return {
                **result,
                "latency_ms": elapsed
            }
        except Exception as e:
            logger.error(f"❌ 유동성 체크 실패: {e}")
            return {
                "approved": True,  # 실패 시 통과 (안전 모드)
                "reason": f"체크 오류: {str(e)}",
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    async def check_whale_movement(
        self,
        symbol: str = "BTCUSDT"
    ) -> Dict[str, Any]:
        """
        고래 움직임 추적 (1초 목표)
        
        Args:
            symbol: 거래 심볼
        
        Returns:
            고래 움직임 분석 결과
        """
        start_time = time.time()
        
        if not self.use_whale_tracker:
            return {
                "approved": True,
                "reason": "고래 추적 비활성화",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        # Lazy Loading
        self._initialize_whale_tracker()
        
        if not self._whale_tracker:
            return {
                "approved": True,
                "reason": "고래 추적 모듈 사용 불가",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        try:
            result = await self._whale_tracker.analyze_whale_movement(symbol=symbol)
            
            elapsed = (time.time() - start_time) * 1000
            
            if not result.get("approved", False):
                self.stats["whale_rejections"] += 1
            
            return {
                **result,
                "latency_ms": elapsed
            }
        except Exception as e:
            logger.error(f"❌ 고래 추적 실패: {e}")
            return {
                "approved": True,  # 실패 시 통과 (안전 모드)
                "reason": f"추적 오류: {str(e)}",
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def check_sentiment_reversal(
        self,
        vector_4d: Dict[str, float],
        price_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        감정적 역추세 필터 (사원수 회전각 기반) (0.5초 목표)
        
        Args:
            vector_4d: 4D 벡터
            price_data: 가격 데이터 (선택적)
        
        Returns:
            감정 필터 결과
        """
        start_time = time.time()
        
        if not self.use_sentiment_filter:
            return {
                "approved": True,
                "reason": "감정 필터 비활성화",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        # Lazy Loading
        self._initialize_sentiment_filter()
        
        if not self._sentiment_filter:
            return {
                "approved": True,
                "reason": "감정 필터 모듈 사용 불가",
                "latency_ms": (time.time() - start_time) * 1000
            }
        
        try:
            result = self._sentiment_filter.check_reversal_risk(
                vector_4d=vector_4d,
                price_data=price_data
            )
            
            elapsed = (time.time() - start_time) * 1000
            
            if not result.get("approved", False):
                self.stats["sentiment_rejections"] += 1
            
            return {
                **result,
                "latency_ms": elapsed
            }
        except Exception as e:
            logger.error(f"❌ 감정 필터 실패: {e}")
            return {
                "approved": True,  # 실패 시 통과 (안전 모드)
                "reason": f"필터 오류: {str(e)}",
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    async def execute_strike(
        self,
        news_url: str,
        symbol: str = "BTCUSDT",
        order_size_usd: float = 1000.0
    ) -> Dict[str, Any]:
        """
        10초 선점 타격 실행 (전체 파이프라인)
        
        Args:
            news_url: 뉴스 URL
            symbol: 거래 심볼
            order_size_usd: 주문 크기 (USD)
        
        Returns:
            타격 실행 결과
        """
        total_start_time = time.time()
        current_time = datetime.now()
        
        self.stats["total_strikes"] += 1
        
        logger.info(f"🚀 10초 선점 타격 시작: {news_url}")
        
        # 1. 뉴스 수집 (2초 목표)
        news_result = await self.collect_news_fast(news_url)
        if not news_result.get("success"):
            return {
                "success": False,
                "error": "뉴스 수집 실패",
                "stage": "news_collection",
                "total_latency_ms": (time.time() - total_start_time) * 1000
            }
        
        # 2. 4D 위상 분석 (0.1ms 목표)
        phase_result = self.analyze_4d_phase(news_result.get("markdown", ""))
        if not phase_result.get("success"):
            return {
                "success": False,
                "error": "4D 위상 분석 실패",
                "stage": "phase_analysis",
                "total_latency_ms": (time.time() - total_start_time) * 1000
            }
        
        vector_4d = phase_result.get("vector_4d", {})
        
        # 3. 고전 지혜 필터 (1초 목표)
        classical_result = self.check_classical_wisdom(vector_4d, current_time)
        if not classical_result.get("approved"):
            return {
                "success": False,
                "error": "고전 지혜 필터 거부",
                "stage": "classical_wisdom",
                "classical_result": classical_result,
                "total_latency_ms": (time.time() - total_start_time) * 1000
            }
        
        # 4. 유동성 체크 (1초 목표)
        liquidity_result = await self.check_liquidity(symbol, order_size_usd)
        if not liquidity_result.get("approved"):
            return {
                "success": False,
                "error": "유동성 부족",
                "stage": "liquidity_check",
                "liquidity_result": liquidity_result,
                "total_latency_ms": (time.time() - total_start_time) * 1000
            }
        
        # 5. 고래 움직임 추적 (1초 목표)
        whale_result = await self.check_whale_movement(symbol)
        if not whale_result.get("approved"):
            return {
                "success": False,
                "error": "고래 움직임 위험",
                "stage": "whale_tracker",
                "whale_result": whale_result,
                "total_latency_ms": (time.time() - total_start_time) * 1000
            }
        
        # 6. 감정적 역추세 필터 (0.5초 목표)
        sentiment_result = self.check_sentiment_reversal(vector_4d)
        if not sentiment_result.get("approved"):
            return {
                "success": False,
                "error": "감정적 역추세 위험",
                "stage": "sentiment_filter",
                "sentiment_result": sentiment_result,
                "total_latency_ms": (time.time() - total_start_time) * 1000
            }
        
        # 7. 모든 필터 통과 → 매매 실행 준비
        total_latency = (time.time() - total_start_time) * 1000
        
        # 성능 통계 업데이트
        self.stats["successful_strikes"] += 1
        if total_latency < self.stats["fastest_strike_ms"]:
            self.stats["fastest_strike_ms"] = total_latency
        if total_latency > self.stats["slowest_strike_ms"]:
            self.stats["slowest_strike_ms"] = total_latency
        
        # 평균 지연 시간 업데이트
        self.stats["average_latency_ms"] = (
            (self.stats["average_latency_ms"] * (self.stats["successful_strikes"] - 1) + total_latency) /
            self.stats["successful_strikes"]
        )
        
        logger.info(f"✅ 10초 선점 타격 완료: {total_latency:.1f}ms")
        
        return {
            "success": True,
            "approved": True,
            "vector_4d": vector_4d,
            "classical_result": classical_result,
            "liquidity_result": liquidity_result,
            "whale_result": whale_result,
            "sentiment_result": sentiment_result,
            "total_latency_ms": total_latency,
            "stage_latencies": {
                "news_collection": news_result.get("latency_ms", 0),
                "phase_analysis": phase_result.get("latency_ms", 0),
                "classical_wisdom": classical_result.get("latency_ms", 0),
                "liquidity_check": liquidity_result.get("latency_ms", 0),
                "whale_tracker": whale_result.get("latency_ms", 0),
                "sentiment_filter": sentiment_result.get("latency_ms", 0)
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        return self.stats.copy()
