#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 Athena Router 통합 모듈 (비트코인 트레이딩)

목적: 이중 트랙 전략과 Athena Router 융합
- CryptoNitroLiveTrader에 Context-Aware Theory Selector 통합
- 거래 신호 생성 시 상황에 따라 필요한 이론만 선택
- 이론 과부하 해결로 연산 속도 향상 (50-70%)

작성일: 2026-01-22
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 예언 리포트 동기화 모듈
try:
    from .prophecy_sync import load_prophecy_distance, adjust_weights_by_prophecy
    PROPHECY_SYNC_AVAILABLE = True
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from prophecy_sync import load_prophecy_distance, adjust_weights_by_prophecy
        PROPHECY_SYNC_AVAILABLE = True
    except ImportError:
        PROPHECY_SYNC_AVAILABLE = False
        logger.warning("⚠️ prophecy_sync 모듈 로드 실패 (예언 리포트 동기화 비활성화)")

WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent

# Athena Router import (여러 경로 시도)
ATHENA_ROUTER_AVAILABLE = False
AthenaRouter = None
QuestionCategory = None

# 경로 1: mkm_sovereign_core 패키지 (우선)
try:
    from mkm_sovereign_core import AthenaRouter
    # QuestionCategory는 tools/core에서 import (mkm_sovereign_core에는 없을 수 있음)
    try:
        sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))
        from athena_router import QuestionCategory
    except ImportError:
        # QuestionCategory가 없어도 계속 진행 (선택적)
        QuestionCategory = None
    ATHENA_ROUTER_AVAILABLE = True
    logger.info("✅ AthenaRouter 로드 완료 (mkm_sovereign_core)")
except ImportError:
    # 경로 2: tools/core/athena_router.py (Fallback)
    try:
        sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))
        from athena_router import AthenaRouter, QuestionCategory
        ATHENA_ROUTER_AVAILABLE = True
        logger.info("✅ AthenaRouter 로드 완료 (tools/core)")
    except ImportError:
        # 경로 3: 상대 경로
        try:
            athena_router_path = WORKSPACE_ROOT / "tools" / "core" / "athena_router.py"
            if athena_router_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("athena_router", athena_router_path)
                athena_router_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(athena_router_module)
                AthenaRouter = athena_router_module.AthenaRouter
                QuestionCategory = athena_router_module.QuestionCategory
                ATHENA_ROUTER_AVAILABLE = True
                logger.info("✅ AthenaRouter 로드 완료 (직접 import)")
            else:
                logger.warning("⚠️ AthenaRouter 파일을 찾을 수 없습니다.")
        except Exception as e:
            logger.warning(f"⚠️ AthenaRouter 로드 실패: {e}")

# TheoryFusionSelector import (여러 경로 시도)
THEORY_FUSION_AVAILABLE = False
TheoryFusionSelector = None
TheoryType = None
TheoryConfig = None

# 경로 1: tools/tools/core/TheoryFusionSelector.py
try:
    sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "tools" / "core"))
    from TheoryFusionSelector import TheoryFusionSelector, TheoryType, TheoryConfig
    THEORY_FUSION_AVAILABLE = True
    logger.info("✅ TheoryFusionSelector 로드 완료 (tools/tools/core)")
except ImportError:
    # 경로 2: 상대 경로
    try:
        theory_selector_path = WORKSPACE_ROOT / "tools" / "tools" / "core" / "TheoryFusionSelector.py"
        if theory_selector_path.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("TheoryFusionSelector", theory_selector_path)
            theory_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(theory_module)
            TheoryFusionSelector = theory_module.TheoryFusionSelector
            TheoryType = theory_module.TheoryType
            TheoryConfig = theory_module.TheoryConfig
            THEORY_FUSION_AVAILABLE = True
            logger.info("✅ TheoryFusionSelector 로드 완료 (직접 import)")
        else:
            logger.warning("⚠️ TheoryFusionSelector 파일을 찾을 수 없습니다.")
    except Exception as e:
        logger.warning(f"⚠️ TheoryFusionSelector 로드 실패: {e}")


class TradingAthenaRouter:
    """
    트레이딩 전용 Athena Router
    
    기능:
    1. 거래 신호 생성 시 상황 분석 (시장 상태, 변동성 등)
    2. 상황에 따라 필요한 이론만 선택 (이론 과부하 해결)
    3. 선택된 이론만으로 신호 생성 (연산 속도 향상)
    4. 도메인별 코드북 라우팅 (데이터 과부하 해결) ⭐ NEW
    """
    
    def __init__(self, use_codebook_router: bool = True):
        """
        초기화
        
        Args:
            use_codebook_router: MKMDomainCodebookRouter 사용 여부
        """
        logger.info("🧠 TradingAthenaRouter 초기화 중...")
        
        # Athena Router 초기화
        if ATHENA_ROUTER_AVAILABLE and AthenaRouter:
            try:
                self.router = AthenaRouter()
                logger.info("✅ AthenaRouter 로드 완료")
            except Exception as e:
                logger.warning(f"⚠️ AthenaRouter 초기화 실패: {e}")
                self.router = None
        else:
            self.router = None
        
        # TheoryFusionSelector 초기화 (Fallback)
        if THEORY_FUSION_AVAILABLE and TheoryFusionSelector:
            try:
                self.theory_selector = TheoryFusionSelector()
                logger.info("✅ TheoryFusionSelector 로드 완료")
            except Exception as e:
                logger.warning(f"⚠️ TheoryFusionSelector 초기화 실패: {e}")
                self.theory_selector = None
        else:
            self.theory_selector = None
        
        # ⭐ MKMDomainCodebookRouter 초기화 (MoE 구조) - MKM-Sovereign-Core 패키지 사용
        self.codebook_router = None
        if use_codebook_router:
            try:
                # MKM-Sovereign-Core 패키지에서 import (우선)
                from mkm_sovereign_core import MKMDomainCodebookRouter, Domain
                
                self.codebook_router = MKMDomainCodebookRouter(
                    embedding_model="all-MiniLM-L6-v2",
                    codebook_size_per_domain=10000
                )
                
                # 코드북 로드 시도
                codebook_dir = WORKSPACE_ROOT / "data" / "mkm_domain_codebooks"
                if codebook_dir.exists():
                    # 각 도메인별 코드북 로드
                    for domain in Domain:
                        codebook_file = codebook_dir / f"{domain.value}.bin"
                        if codebook_file.exists():
                            try:
                                self.codebook_router.load_domain_codebook(domain, codebook_file)
                                logger.info(f"✅ {domain.value} 도메인 코드북 로드 완료")
                            except Exception as e:
                                logger.warning(f"⚠️ {domain.value} 도메인 코드북 로드 실패: {e}")
                    logger.info("✅ MKMDomainCodebookRouter 로드 완료 (코드북 로드됨)")
                else:
                    logger.info("✅ MKMDomainCodebookRouter 로드 완료 (코드북 미구축, 나중에 구축 필요)")
            except ImportError:
                # Fallback: tools/core에서 import 시도
                try:
                    sys.path.insert(0, str(WORKSPACE_ROOT / "tools" / "core"))
                    from mkm_domain_codebook_router import MKMDomainCodebookRouter, Domain
                    
                    self.codebook_router = MKMDomainCodebookRouter(
                        embedding_model="all-MiniLM-L6-v2",
                        codebook_size_per_domain=10000
                    )
                    logger.info("✅ MKMDomainCodebookRouter 로드 완료 (Fallback: tools/core)")
                except Exception as e:
                    logger.warning(f"⚠️ MKMDomainCodebookRouter 초기화 실패: {e}")
                    self.codebook_router = None
            except Exception as e:
                logger.warning(f"⚠️ MKMDomainCodebookRouter 초기화 실패: {e}")
                self.codebook_router = None
        
        logger.info("✅ TradingAthenaRouter 초기화 완료")
    
    def analyze_market_context(
        self,
        market_data: Dict[str, Any],
        volatility: float,
        trend: str
    ) -> str:
        """
        시장 상황 분석 및 카테고리 결정
        
        Args:
            market_data: 시장 데이터
            volatility: 변동성
            trend: 추세 (up/down/sideways)
        
        Returns:
            질문 카테고리 문자열
        """
        # 시장 상황을 질문으로 변환
        question = f"비트코인 시장 상황: 변동성 {volatility:.2f}, 추세 {trend}"
        
        if self.router:
            try:
                # Athena Router로 질문 분류
                category, category_scores = self.router.classify_question(question)
                return category.value
            except Exception as e:
                logger.warning(f"⚠️ 질문 분류 실패: {e}")
        
        # Fallback: 변동성 기반 분류
        if volatility > 0.05:
            return "investment"  # 고변동성 → 투자/금융
        else:
            return "prediction"  # 저변동성 → 예측
    
    def _evaluate_search_quality(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> float:
        """
        검색 결과 품질 평가 (검색 품질 70.11% 활용)
        
        평가 항목:
        1. 검색 결과 개수 (0.15)
        2. 유사도 점수 (0.35)
        3. 키워드 매칭 (0.25)
        4. 결과 다양성 (0.15)
        5. 최상위 결과 품질 (0.10)
        
        Args:
            query: 검색 쿼리
            search_results: 검색 결과 리스트
        
        Returns:
            품질 점수 (0.0 ~ 1.0)
        """
        import numpy as np
        
        if not search_results:
            return 0.0
        
        # 1. 검색 결과 개수 기반 점수 (최대 0.15)
        optimal_count = 5
        count_score = min(0.15, len(search_results) / optimal_count * 0.15)
        
        # 2. 유사도 기반 점수 (최대 0.35)
        similarity_scores = [r.get('score', 0.0) for r in search_results if isinstance(r, dict)]
        if similarity_scores:
            avg_similarity = np.mean(similarity_scores)
            max_similarity = np.max(similarity_scores)
            weighted_similarity = (avg_similarity * 0.6 + max_similarity * 0.4)
            similarity_score = weighted_similarity * 0.35
        else:
            similarity_score = 0.3 * 0.35
        
        # 3. 키워드 매칭 점수 (최대 0.25)
        query_keywords = set(query.lower().split())
        keyword_match_scores = []
        for result in search_results[:5]:
            text = result.get('text', '') if isinstance(result, dict) else ''
            if text:
                text_keywords = set(text.lower().split())
                intersection = len(query_keywords & text_keywords)
                union = len(query_keywords | text_keywords)
                jaccard = intersection / union if union > 0 else 0.0
                keyword_match_scores.append(jaccard)
        
        keyword_score = np.mean(keyword_match_scores) * 0.25 if keyword_match_scores else 0.0
        
        # 4. 결과 다양성 점수 (최대 0.15)
        if len(search_results) >= 3:
            text_lengths = [len(r.get('text', '')) for r in search_results[:3] if isinstance(r, dict)]
            if text_lengths:
                length_std = np.std(text_lengths)
                length_mean = np.mean(text_lengths)
                diversity = min(1.0, length_std / (length_mean * 0.2 + 1e-8))
                diversity_score = diversity * 0.15
            else:
                diversity_score = 0.0
        else:
            diversity_score = 0.0
        
        # 5. 최상위 결과 품질 점수 (최대 0.10)
        if search_results:
            top_result = search_results[0]
            top_text = top_result.get('text', '') if isinstance(top_result, dict) else ''
            if top_text:
                top_length_score = min(1.0, len(top_text) / 100.0)
                top_keywords = set(top_text.lower().split())
                top_keyword_match = len(query_keywords & top_keywords) / len(query_keywords) if query_keywords else 0.0
                top_quality_score = (top_length_score * 0.5 + top_keyword_match * 0.5) * 0.10
            else:
                top_quality_score = 0.0
        else:
            top_quality_score = 0.0
        
        # 총점 계산
        total_score = count_score + similarity_score + keyword_score + diversity_score + top_quality_score
        
        # 정규화: 점수 분포를 0.3 ~ 1.0 범위로 조정
        normalized_score = 0.3 + (total_score * 0.7)
        
        return min(1.0, max(0.0, normalized_score))
    
    def _get_search_quality_from_codebook(
        self,
        query: str,
        detected_domain: Any
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        코드북에서 검색 품질 점수 계산
        
        Args:
            query: 검색 쿼리
            detected_domain: 감지된 도메인
        
        Returns:
            (검색 품질 점수, 검색 결과 리스트)
        """
        if not self.codebook_router or not detected_domain:
            return 0.0, []
        
        try:
            # 쿼리 벡터화
            query_vector = self.codebook_router.brain.encode([query], convert_to_numpy=True)[0]
            
            # 도메인 코드북으로 양자화
            index = self.codebook_router.quantize_vector(query_vector, detected_domain)
            
            # 유사한 인덱스 찾기 (주변 인덱스 검색)
            codebook = self.codebook_router.domain_codebooks.get(detected_domain)
            if codebook is None or len(codebook) == 0:
                return 0.0, []
            
            # 코사인 유사도 계산
            codebook_vectors = np.array(codebook)
            similarities = np.dot(codebook_vectors, query_vector) / (
                np.linalg.norm(codebook_vectors, axis=1) * np.linalg.norm(query_vector) + 1e-8
            )
            
            # 상위 5개 결과 선택
            top_indices = np.argsort(similarities)[-5:][::-1]
            search_results = []
            for idx in top_indices:
                text = self.codebook_router.get_original_text(idx, detected_domain)
                if text:
                    search_results.append({
                        "index": int(idx),
                        "text": text,
                        "score": float(similarities[idx])
                    })
            
            # 검색 품질 평가
            quality_score = self._evaluate_search_quality(query, search_results)
            
            return quality_score, search_results
            
        except Exception as e:
            logger.warning(f"⚠️ 검색 품질 계산 실패: {e}")
            return 0.0, []
    
    def select_trading_theories(
        self,
        market_data: Dict[str, Any],
        volatility: float,
        trend: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        거래 신호 생성에 필요한 이론만 선택 (검색 품질 통합)
        
        Args:
            market_data: 시장 데이터
            volatility: 변동성
            trend: 추세
            context: 추가 컨텍스트
        
        Returns:
            선택된 이론 설정 딕셔너리 (search_quality 점수 포함)
        """
        logger.info("🧠 거래 이론 자동 선택 시작...")
        
        # 1. 시장 상황 분석
        category = self.analyze_market_context(market_data, volatility, trend)
        
        # ⭐ 2. 도메인 감지 (MoE 구조) - 이론 선택 전에 도메인 코드북 선택
        detected_domain = None
        search_quality = 0.0
        search_results = []
        
        if self.codebook_router:
            try:
                market_situation = f"비트코인 시장: 변동성 {volatility:.2f}, 추세 {trend}"
                # Phase 3: 하이브리드 도메인 감지 사용 (키워드 + 벡터 + 4D 분석)
                detected_domain = self.codebook_router.detect_domain(market_situation, use_hybrid=True)
                logger.info(f"🎯 도메인 감지: {detected_domain.value} (하이브리드 MoE 구조)")
                
                # 거래 신호 생성 시 T (Trading) 도메인 강제 (시장 분석 시 K 도메인)
                if "거래 신호" in market_situation or "매수" in market_situation or "매도" in market_situation:
                    detected_domain = Domain.TRADING
                    logger.info(f"🎯 거래 신호 감지 → T (Trading) 도메인 강제")
                elif "시장 분석" in market_situation or "투자" in market_situation:
                    detected_domain = Domain.KNOWLEDGE
                    logger.info(f"🎯 시장 분석 감지 → K (Knowledge) 도메인 강제")
                
                # ⭐ 검색 품질 점수 계산 (70.11% 활용)
                search_quality, search_results = self._get_search_quality_from_codebook(
                    query=market_situation,
                    detected_domain=detected_domain
                )
                logger.info(f"📊 검색 품질 점수: {search_quality:.2%} (검색 결과: {len(search_results)}개)")
                
            except Exception as e:
                logger.warning(f"⚠️ 도메인 감지 실패: {e}")
        
        # 3. Athena Router로 이론 선택
        if self.router:
            try:
                # 시장 상황을 질문으로 변환
                question = f"비트코인 거래 신호 생성: 변동성 {volatility:.2f}, 추세 {trend}"
                
                # 이론 선택
                result = self.router.select_theories(question, context)
                
                # ⭐ 도메인 정보 및 검색 품질 추가 (MoE 구조)
                if detected_domain:
                    result["detected_domain"] = detected_domain.value
                    result["codebook_available"] = self.codebook_router.domain_codebooks.get(detected_domain) is not None
                
                # 검색 품질 점수 추가 (70.11% 활용)
                result["search_quality"] = search_quality
                result["search_results_count"] = len(search_results)
                
                logger.info(f"✅ 이론 선택 완료: {len([t for t, c in result.get('selected_theories', {}).items() if c.enabled])}개 이론 활성화 (검색 품질: {search_quality:.2%})")
                
                return result
            except Exception as e:
                logger.warning(f"⚠️ 이론 선택 실패: {e}")
        
        # Fallback: TheoryFusionSelector 사용
        if self.theory_selector:
            try:
                # 도메인 매핑 (crypto_volatile 추가) ⭐
                domain_mapping = {
                    "investment": "finance",
                    "prediction": "general",
                    "general": "general",
                    "crypto": "crypto_volatile",  # 🏛️ Athena v2.5 Nitro: 암호화폐 도메인 매핑
                    "bitcoin": "crypto_volatile",
                    "volatile": "crypto_volatile"
                }
                
                # 변동성 기반 도메인 자동 감지
                if volatility > 0.05:  # 높은 변동성 → crypto_volatile
                    domain = "crypto_volatile"
                    logger.info(f"🎯 높은 변동성 감지 ({volatility:.3f}) → crypto_volatile 도메인 강제")
                else:
                    domain = domain_mapping.get(category, "general")
                
                # TheoryFusionSelector로 이론 선택 (도메인별 가중치 자동 적용)
                base_configs = self.theory_selector.select_theories(domain, context)
                
                # ⭐ 가중치 동적 조정 (변동성 기반 + 검색 품질 기반)
                if domain == "crypto_volatile":
                    # 변동성이 높을수록 HMM과 RL 가중치 증가
                    volatility_factor = min(volatility / 0.1, 1.5)  # 최대 1.5배
                    
                    # 검색 품질 기반 전략 조정 (70.11% 활용)
                    # 검색 품질 70% 이상: 공격적 전략 (HMM, RL 가중치 증가)
                    # 검색 품질 50-70%: 균형 전략 (기본 가중치 유지)
                    # ⭐ 권장안 B: 평균회귀 레짐 시 가중치 분기 (Bayesian 상향, HMM/RL 하향)
                    if context and context.get("use_mean_reversion"):
                        logger.info("📐 use_mean_reversion=True → Bayesian 가중치 상향, HMM/RL 가중치 하향 적용")
                    # 검색 품질 50% 미만: 보수적 전략 (Bayesian Update 가중치 증가)
                    if search_quality >= 0.70:
                        # 공격적 전략: HMM, RL 가중치 증가
                        search_quality_factor = (search_quality - 0.70) / 0.30  # 0.70~1.0 → 0.0~1.0
                        logger.info(f"📊 검색 품질 {search_quality:.2%} → 공격적 전략 (HMM, RL 가중치 증가)")
                    elif search_quality >= 0.50:
                        # 균형 전략: 기본 가중치 유지
                        search_quality_factor = 0.0
                        logger.info(f"📊 검색 품질 {search_quality:.2%} → 균형 전략 (기본 가중치 유지)")
                    else:
                        # 보수적 전략: Bayesian Update 가중치 증가
                        search_quality_factor = -(0.50 - search_quality) / 0.50  # 0.0~0.50 → -1.0~0.0
                        logger.info(f"📊 검색 품질 {search_quality:.2%} → 보수적 전략 (Bayesian Update 가중치 증가)")
                    
                    for theory_type, config in base_configs.items():
                        if theory_type.value == "hmm":
                            # HMM: 변동성 + 검색 품질 (공격적)
                            config.weight *= (1.0 + volatility_factor * 0.2 + search_quality_factor * 0.15)
                        elif theory_type.value == "reinforcement_learning":
                            # RL: 변동성 + 검색 품질 (공격적)
                            config.weight *= (1.0 + volatility_factor * 0.15 + search_quality_factor * 0.10)
                        elif theory_type.value == "bayesian_update":
                            # Bayesian: 변동성 감소 + 검색 품질 (보수적)
                            config.weight *= (1.0 - volatility_factor * 0.1 - search_quality_factor * 0.10)
                        # ⭐ 권장안 B: 레짐 기반 평균회귀 시 Bayesian 상향, HMM/RL 하향
                        if context and context.get("use_mean_reversion"):
                            if theory_type.value == "bayesian_update":
                                config.weight *= 1.15
                            elif theory_type.value in ("hmm", "reinforcement_learning"):
                                config.weight *= 0.85
                    
                    # ⭐ 예언 리포트 동기화 (Divine Distance 기반 자동 비중 조절)
                    if PROPHECY_SYNC_AVAILABLE:
                        try:
                            prophecy_distance = load_prophecy_distance()
                            if prophecy_distance is not None:
                                # 가중치 딕셔너리 생성
                                weight_dict = {
                                    theory_type.value: config.weight 
                                    for theory_type, config in base_configs.items()
                                }
                                
                                # 예언 리포트 기반 가중치 조정
                                adjusted_weights = adjust_weights_by_prophecy(weight_dict, prophecy_distance)
                                
                                # 조정된 가중치 적용
                                for theory_type, config in base_configs.items():
                                    if theory_type.value in adjusted_weights:
                                        config.weight = adjusted_weights[theory_type.value]
                                
                                logger.info(f"🔮 예언 리포트 동기화 완료 (Divine Distance: {prophecy_distance:.4f})")
                        except Exception as e:
                            logger.warning(f"⚠️ 예언 리포트 동기화 실패: {e}")
                    
                    logger.info(f"🎯 변동성 기반 가중치 조정 완료 (factor: {volatility_factor:.2f})")
                
                # 활성화된 이론만 필터링
                selected_configs = {
                    t: c for t, c in base_configs.items() if c.enabled
                }
                
                result = {
                    "category": category,
                    "selected_theories": selected_configs,
                    "confidence": 0.8
                }
                
                # ⭐ 도메인 정보 및 검색 품질 추가 (MoE 구조)
                if detected_domain:
                    result["detected_domain"] = detected_domain.value
                    result["codebook_available"] = self.codebook_router.domain_codebooks.get(detected_domain) is not None if self.codebook_router else False
                
                # 검색 품질 점수 추가 (70.11% 활용)
                result["search_quality"] = search_quality
                result["search_results_count"] = len(search_results)
                
                logger.info(f"✅ 이론 선택 완료 (Fallback): {len(selected_configs)}개 이론 활성화 (검색 품질: {search_quality:.2%})")
                
                return result
            except Exception as e:
                logger.warning(f"⚠️ 이론 선택 실패 (Fallback): {e}")
        
        # 최종 Fallback: 기본 설정
        logger.warning("⚠️ 모든 이론 선택기 실패, 기본 설정 사용")
        return {
            "category": category,
            "selected_theories": {},
            "confidence": 0.5
        }
    
    def get_theory_summary(self, market_data: Dict[str, Any], volatility: float, trend: str) -> str:
        """
        거래 신호 생성에 사용될 이론 요약 반환
        
        Args:
            market_data: 시장 데이터
            volatility: 변동성
            trend: 추세
        
        Returns:
            이론 선택 요약 문자열
        """
        result = self.select_trading_theories(market_data, volatility, trend)
        
        category = result.get("category", "unknown")
        confidence = result.get("confidence", 0.0)
        selected_theories = result.get("selected_theories", {})
        
        enabled_theories = [t.value for t, c in selected_theories.items() if c.enabled] if isinstance(selected_theories, dict) else []
        
        summary = f"""
🧠 TradingAthenaRouter 이론 선택 결과:

📊 시장 상황: 변동성 {volatility:.2f}, 추세 {trend}
🎯 카테고리: {category} (신뢰도: {confidence:.2f})
✅ 활성화된 이론: {', '.join(enabled_theories) if enabled_theories else '없음 (기본 설정 사용)'}
"""
        
        return summary.strip()


def integrate_with_crypto_nitro_live_trader():
    """
    CryptoNitroLiveTrader에 Athena Router 통합
    
    통합 방법:
    1. CryptoNitroLiveTrader 초기화 시 TradingAthenaRouter 추가
    2. 신호 생성 전 이론 선택 수행
    3. 선택된 이론만으로 신호 생성
    """
    logger.info("🔗 CryptoNitroLiveTrader 통합 시작...")
    
    # 통합 가이드 반환
    integration_guide = """
## CryptoNitroLiveTrader 통합 가이드

### 1. CryptoNitroLiveTrader 클래스 수정

```python
from src.integration.athena_router_integration import TradingAthenaRouter

class CryptoNitroLiveTrader:
    def __init__(self, ...):
        # 기존 초기화 코드...
        
        # Athena Router 추가
        self.athena_router = TradingAthenaRouter()
    
    async def calculate_trading_signal(self, market_data):
        # 1. 시장 상황 분석
        volatility = self._calculate_volatility(market_data)
        trend = self._detect_trend(market_data)
        
        # 2. Athena Router로 이론 선택
        theory_result = self.athena_router.select_trading_theories(
            market_data=market_data,
            volatility=volatility,
            trend=trend
        )
        
        # 3. 선택된 이론만으로 신호 생성
        selected_theories = theory_result.get("selected_theories", {})
        
        # 4. 기존 신호 생성 로직 (선택된 이론만 사용)
        signal = self._generate_signal_with_selected_theories(
            market_data=market_data,
            theories=selected_theories
        )
        
        return signal
```

### 2. 이론별 신호 생성 로직

```python
def _generate_signal_with_selected_theories(self, market_data, theories):
    signal_strength = 0.0
    signal_direction = None
    
    # 활성화된 이론만 사용
    for theory_type, config in theories.items():
        if not config.enabled:
            continue
        
        if theory_type == TheoryType.BAYESIAN_UPDATE:
            # 베이즈 업데이트 기반 신호
            signal_strength += self._bayesian_signal(market_data) * config.weight
        
        elif theory_type == TheoryType.MARKOV_CHAIN:
            # 마르코프 체인 기반 신호
            signal_strength += self._markov_signal(market_data) * config.weight
        
        # ... 기타 이론들
    
    return {
        "strength": signal_strength,
        "direction": signal_direction,
        "theories_used": [t.value for t in theories.keys() if theories[t].enabled]
    }
```

### 3. 예상 효과

- 연산 속도: 50-70% 향상 (불필요한 이론 제외)
- 신호 정확도: 향상 (핵심 이론만 집중)
- 시스템 안정성: 향상 (복잡도 감소)
"""
    
    logger.info("✅ 통합 가이드 생성 완료")
    return integration_guide


if __name__ == "__main__":
    # 테스트
    router = TradingAthenaRouter()
    
    # 시뮬레이션 시장 데이터
    market_data = {
        "price": 50000,
        "volume": 1000000,
        "timestamp": "2026-01-22T12:00:00"
    }
    
    volatility = 0.03
    trend = "up"
    
    # 이론 선택 테스트
    result = router.select_trading_theories(market_data, volatility, trend)
    summary = router.get_theory_summary(market_data, volatility, trend)
    
    logger.info("\n" + "=" * 80)
    logger.info(summary)
    logger.info("=" * 80)
    
    # 통합 가이드 출력
    integration_guide = integrate_with_crypto_nitro_live_trader()
    logger.info("\n" + integration_guide)

