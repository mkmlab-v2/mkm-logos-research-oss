#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chart Image Analyzer (차트 이미지 분석기)

목적: 비트코인 차트 이미지를 생성하고 Gemini Vision API로 분석
- TradingView 스타일 차트 생성
- Gemini Vision API로 차트 패턴 인식
- 시각적 신호와 이론 신호 융합

작성일: 2026-01-30
상태: ✅ 구축 완료
"""

import sys
import os
import base64
import io
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

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

# matplotlib (차트 생성용)
try:
    import matplotlib
    matplotlib.use('Agg')  # 백엔드 설정 (GUI 없이)
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("⚠️ matplotlib 미설치, 차트 생성 불가")

# Gemini Vision API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("⚠️ google-generativeai 미설치, Gemini Vision API 사용 불가")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChartImageAnalyzer:
    """
    차트 이미지 분석기
    
    기능:
    1. 비트코인 차트 이미지 생성 (TradingView 스타일)
    2. Gemini Vision API로 차트 패턴 인식
    3. 시각적 신호 추출
    """
    
    def __init__(
        self, 
        gemini_api_key: Optional[str] = None,
        analysis_interval: int = 3600,  # 차트 분석 간격 (초, 기본값: 1시간)
        enable_cache: bool = True,  # 캐싱 활성화
        cache_ttl: int = 3600  # 캐시 유효 시간 (초, 기본값: 1시간)
    ):
        """
        Args:
            gemini_api_key: Gemini API 키 (환경 변수에서 자동 로드 가능)
            analysis_interval: 차트 분석 간격 (초, 기본값: 3600 = 1시간)
            enable_cache: 캐싱 활성화 여부
            cache_ttl: 캐시 유효 시간 (초, 기본값: 3600 = 1시간)
        """
        self.gemini_available = False
        self.gemini_model = None
        
        # 할당량 최적화 설정
        self.analysis_interval = analysis_interval
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.last_analysis_time: Optional[datetime] = None
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}  # 차트 해시 -> 분석 결과
        
        # Nitro Compression Engine 초기화
        self.nitro_compression = None
        if NITRO_COMPRESSION_AVAILABLE:
            try:
                self.nitro_compression = NitroCompressionEngine(compression_level=6)
                logger.info("✅ Nitro Compression Engine 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Nitro Compression Engine 초기화 실패: {e}")
        
        # Gemini API 초기화
        if GEMINI_AVAILABLE:
            api_key = gemini_api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    # 사용 가능한 모델 자동 선택 (우선순위: gemini-2.0-flash > gemini-2.5-flash)
                    try:
                        models = genai.list_models()
                        available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                        model_name = 'gemini-2.0-flash'  # 기본값
                        for preferred in ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']:
                            for m in available_models:
                                if preferred in m:
                                    model_name = m.split('/')[-1]
                                    break
                            if model_name != 'gemini-2.0-flash':
                                break
                        self.gemini_model = genai.GenerativeModel(model_name)
                        self.gemini_available = True
                        logger.info(f"✅ Gemini Vision API 초기화 완료 (모델: {model_name})")
                    except Exception as e2:
                        logger.warning(f"⚠️ 모델 자동 선택 실패, 기본 모델 사용: {e2}")
                        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
                        self.gemini_available = True
                    logger.info("✅ Gemini Vision API 초기화 완료")
                except Exception as e:
                    logger.warning(f"⚠️ Gemini API 초기화 실패: {e}")
            else:
                logger.warning("⚠️ Gemini API 키가 설정되지 않았습니다")
        else:
            logger.warning("⚠️ google-generativeai 미설치, Gemini Vision API 사용 불가")
        
        # matplotlib 사용 가능 여부 확인
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("⚠️ matplotlib 미설치, 차트 생성 불가")
    
    def generate_chart_image(
        self,
        price_data: pd.DataFrame,
        indicators: Optional[Dict[str, pd.Series]] = None,
        style: str = "tradingview"
    ) -> Optional[str]:
        """
        비트코인 차트 이미지 생성 (TradingView 스타일)
        
        Args:
            price_data: 가격 데이터 (OHLCV)
            indicators: 기술적 지표 (선택적)
            style: 차트 스타일 ("tradingview", "candlestick", "line")
        
        Returns:
            Base64 인코딩된 이미지 문자열 (없으면 None)
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("❌ matplotlib 미설치, 차트 생성 불가")
            return None
        
        try:
            # Figure 생성
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[3, 1])
            fig.patch.set_facecolor('#1e1e1e')  # 다크 배경
            ax1.set_facecolor('#1e1e1e')
            ax2.set_facecolor('#1e1e1e')
            
            # 가격 데이터 준비
            if 'timestamp' in price_data.columns:
                dates = pd.to_datetime(price_data['timestamp'])
            else:
                dates = pd.date_range(end=datetime.now(), periods=len(price_data), freq='1H')
            
            # 캔들스틱 차트 생성
            if style == "tradingview" or style == "candlestick":
                # 상승 캔들 (녹색)
                up_candles = price_data[price_data['close'] >= price_data['open']]
                # 하락 캔들 (빨간색)
                down_candles = price_data[price_data['close'] < price_data['open']]
                
                # 상승 캔들 그리기
                for idx, row in up_candles.iterrows():
                    date_idx = dates[idx] if isinstance(idx, int) else dates[price_data.index.get_loc(idx)]
                    color = '#26a69a'  # TradingView 녹색
                    # 몸통
                    ax1.bar(date_idx, row['close'] - row['open'], bottom=row['open'], 
                           width=0.8, color=color, edgecolor=color)
                    # 위 꼬리
                    ax1.plot([date_idx, date_idx], [row['high'], row['close']], 
                            color=color, linewidth=1.5)
                    # 아래 꼬리
                    ax1.plot([date_idx, date_idx], [row['low'], row['open']], 
                            color=color, linewidth=1.5)
                
                # 하락 캔들 그리기
                for idx, row in down_candles.iterrows():
                    date_idx = dates[idx] if isinstance(idx, int) else dates[price_data.index.get_loc(idx)]
                    color = '#ef5350'  # TradingView 빨간색
                    # 몸통
                    ax1.bar(date_idx, row['open'] - row['close'], bottom=row['close'], 
                           width=0.8, color=color, edgecolor=color)
                    # 위 꼬리
                    ax1.plot([date_idx, date_idx], [row['high'], row['open']], 
                            color=color, linewidth=1.5)
                    # 아래 꼬리
                    ax1.plot([date_idx, date_idx], [row['low'], row['close']], 
                            color=color, linewidth=1.5)
            else:
                # 라인 차트
                ax1.plot(dates, price_data['close'], color='#26a69a', linewidth=2, label='Price')
            
            # 기술적 지표 추가
            if indicators:
                if 'sma_20' in indicators:
                    ax1.plot(dates, indicators['sma_20'], color='#ff9800', linewidth=1.5, 
                            label='SMA 20', alpha=0.7)
                if 'sma_50' in indicators:
                    ax1.plot(dates, indicators['sma_50'], color='#2196f3', linewidth=1.5, 
                            label='SMA 50', alpha=0.7)
                if 'ema_12' in indicators:
                    ax1.plot(dates, indicators['ema_12'], color='#9c27b0', linewidth=1.5, 
                            label='EMA 12', alpha=0.7)
            
            # 거래량 차트
            if 'volume' in price_data.columns:
                colors = ['#26a69a' if price_data.iloc[i]['close'] >= price_data.iloc[i]['open'] 
                         else '#ef5350' for i in range(len(price_data))]
                ax2.bar(dates, price_data['volume'], color=colors, alpha=0.6, width=0.8)
            
            # 스타일링
            ax1.set_ylabel('Price (USDT)', color='white', fontsize=12)
            ax1.set_title('Bitcoin Price Chart', color='white', fontsize=14, fontweight='bold')
            ax1.tick_params(colors='white')
            ax1.grid(True, alpha=0.3, color='gray')
            ax1.legend(loc='upper left', facecolor='#1e1e1e', edgecolor='gray', labelcolor='white')
            
            ax2.set_ylabel('Volume', color='white', fontsize=12)
            ax2.set_xlabel('Time', color='white', fontsize=12)
            ax2.tick_params(colors='white')
            ax2.grid(True, alpha=0.3, color='gray')
            
            # 날짜 포맷
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 레이아웃 조정
            plt.tight_layout()
            
            # 이미지를 Base64로 변환
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, facecolor='#1e1e1e', 
                       bbox_inches='tight', pad_inches=0.1)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            buffer.close()
            plt.close(fig)
            
            logger.info("✅ 차트 이미지 생성 완료")
            return image_base64
            
        except Exception as e:
            logger.error(f"❌ 차트 이미지 생성 실패: {e}")
            return None
    
    def should_analyze_chart(self) -> bool:
        """
        차트 분석이 필요한지 확인 (할당량 최적화)
        
        Returns:
            분석 필요 여부
        """
        # 캐싱 비활성화 시 항상 분석
        if not self.enable_cache:
            return True
        
        # 마지막 분석 시간 확인
        if not self.last_analysis_time:
            return True
        
        # 분석 간격 확인
        time_since_last = datetime.now() - self.last_analysis_time
        return time_since_last.total_seconds() >= self.analysis_interval
    
    def get_chart_hash(self, chart_image_base64: str) -> str:
        """
        차트 이미지 해시 생성 (캐싱용)
        
        Args:
            chart_image_base64: Base64 인코딩된 차트 이미지
        
        Returns:
            차트 해시 문자열
        """
        # Base64 헤더 제거
        if ',' in chart_image_base64:
            chart_image_base64 = chart_image_base64.split(',')[1]
        
        # MD5 해시 생성
        return hashlib.md5(chart_image_base64.encode()).hexdigest()
    
    async def analyze_chart_pattern(
        self,
        chart_image_base64: str,
        current_price: float,
        current_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Gemini Vision API로 차트 패턴 분석 (캐싱 지원)
        
        Args:
            chart_image_base64: Base64 인코딩된 차트 이미지
            current_price: 현재 가격
            current_analysis: 현재 분석 결과 (선택적)
        
        Returns:
            차트 분석 결과 딕셔너리
        """
        if not self.gemini_available or not self.gemini_model:
            logger.warning("⚠️ Gemini Vision API 사용 불가, 기본 결과 반환")
            return self._get_default_chart_analysis()
        
        # 캐싱 확인
        if self.enable_cache:
            chart_hash = self.get_chart_hash(chart_image_base64)
            
            if chart_hash in self.analysis_cache:
                cached_result = self.analysis_cache[chart_hash]
                cache_timestamp = cached_result.get('timestamp')
                
                # 캐시 유효 시간 확인
                if cache_timestamp:
                    time_since_cache = datetime.now() - cache_timestamp
                    if time_since_cache.total_seconds() < self.cache_ttl:
                        logger.info(f"✅ 차트 분석 캐시 사용 (캐시 시간: {time_since_cache.total_seconds():.0f}초 전)")
                        
                        # 압축된 캐시 데이터 복원
                        if cached_result.get('compressed', False) and self.nitro_compression:
                            try:
                                compressed_data = base64.b64decode(cached_result.get('result_compressed', ''))
                                result_dict = self.nitro_compression.decompress_json(compressed_data)
                                logger.debug("✅ 캐시 데이터 압축 해제 완료 (니트로 압축)")
                                return result_dict
                            except Exception as e:
                                logger.warning(f"⚠️ 캐시 압축 해제 실패: {e}")
                                # 일반 캐시로 폴백
                                if 'result' in cached_result:
                                    return cached_result['result']
                        else:
                            # 일반 캐시
                            return cached_result.get('result', self._get_default_chart_analysis())
                else:
                    # 타임스탬프가 없으면 캐시 무효화
                    del self.analysis_cache[chart_hash]
        
        # 분석 간격 확인
        if not self.should_analyze_chart():
            time_since_last = datetime.now() - self.last_analysis_time if self.last_analysis_time else timedelta(0)
            remaining = self.analysis_interval - time_since_last.total_seconds()
            logger.info(f"⏸️ 차트 분석 간격 대기 중 (남은 시간: {remaining:.0f}초)")
            return self._get_default_chart_analysis()
        
        try:
            # 분석 프롬프트 (기본)
            base_prompt = f"""
이 비트코인 차트 이미지를 분석하여 다음 정보를 JSON 형식으로 제공해주세요:

현재 상황:
- 현재 가격: ${current_price:,.2f}
- TheoryFusion 신호: {current_analysis.get('fusion_signal', 'N/A') if current_analysis else 'N/A'}
- 신뢰도: {f"{current_analysis.get('confidence', 0):.2%}" if current_analysis else 'N/A'}

다음 정보를 분석해주세요:

1. **차트 패턴 인식**:
   - 헤드앤숄더 (Head and Shoulders)
   - 역헤드앤숄더 (Inverse Head and Shoulders)
   - 삼각형 (Triangle)
   - 플래그 (Flag)
   - 페넌트 (Pennant)
   - 더블 탑/바텀 (Double Top/Bottom)
   - 기타 패턴

2. **추세 분석**:
   - 상승 추세 (Uptrend)
   - 하락 추세 (Downtrend)
   - 횡보 (Sideways)
   - 추세 전환 가능성

3. **지지/저항선**:
   - 주요 지지선 가격
   - 주요 저항선 가격
   - 돌파 가능성

4. **시각적 신호**:
   - 매수 신호 강도 (0.0 ~ 1.0)
   - 매도 신호 강도 (0.0 ~ 1.0)
   - 신뢰도 (0.0 ~ 1.0)

5. **권장 사항**:
   - 매수/매도/보류 중 선택
   - 이유 설명

다음 JSON 형식으로 응답해주세요:
{{
  "patterns": ["패턴1", "패턴2"],
  "trend": "상승|하락|횡보",
  "support_level": 가격,
  "resistance_level": 가격,
  "buy_signal_strength": 0.0-1.0,
  "sell_signal_strength": 0.0-1.0,
  "confidence": 0.0-1.0,
  "recommendation": "BUY|SELL|HOLD",
  "reasoning": "분석 이유"
}}

⚠️ 중요: 정확한 정보만 추출하고, 불확실한 내용은 보수적으로 평가해주세요.
"""
            
            # Nitro Compression으로 프롬프트 최적화
            if self.nitro_compression:
                analysis_prompt = self.nitro_compression.optimize_prompt_for_gemini(base_prompt, max_tokens=500)
                logger.debug("✅ 프롬프트 최적화 완료 (니트로 압축)")
            else:
                analysis_prompt = base_prompt
            
            # Base64 헤더 제거 (이미 제거된 경우 그대로 사용)
            if ',' in chart_image_base64:
                chart_image_base64 = chart_image_base64.split(',')[1]
            
            # Gemini Vision API 호출
            result = self.gemini_model.generate_content([
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": chart_image_base64
                    }
                },
                {"text": analysis_prompt}
            ])
            
            response_text = result.text
            
            # JSON 추출 (마크다운 코드 블록 제거)
            json_str = response_text.replace('```json', '').replace('```', '').strip()
            analysis_result = json.loads(json_str)
            
            # 분석 결과 생성
            result_dict = {
                'success': True,
                'analysis': analysis_result,
                'timestamp': datetime.now().isoformat()
            }
            
            # 캐싱 저장 (Nitro Compression 적용)
            if self.enable_cache:
                chart_hash = self.get_chart_hash(chart_image_base64)
                
                # Nitro Compression으로 캐시 데이터 압축
                if self.nitro_compression:
                    try:
                        compressed_result = self.nitro_compression.compress_json(result_dict)
                        self.analysis_cache[chart_hash] = {
                            'result_compressed': base64.b64encode(compressed_result).decode('utf-8'),
                            'timestamp': datetime.now(),
                            'compressed': True
                        }
                        logger.debug("✅ 캐시 데이터 압축 저장 완료 (니트로 압축)")
                    except Exception as e:
                        logger.warning(f"⚠️ 캐시 압축 실패, 일반 저장: {e}")
                        self.analysis_cache[chart_hash] = {
                            'result': result_dict,
                            'timestamp': datetime.now(),
                            'compressed': False
                        }
                else:
                    self.analysis_cache[chart_hash] = {
                        'result': result_dict,
                        'timestamp': datetime.now(),
                        'compressed': False
                    }
                
                # 캐시 크기 제한 (최대 100개)
                if len(self.analysis_cache) > 100:
                    # 가장 오래된 캐시 삭제
                    oldest_key = min(self.analysis_cache.keys(), 
                                   key=lambda k: self.analysis_cache[k].get('timestamp', datetime.min))
                    del self.analysis_cache[oldest_key]
            
            # 마지막 분석 시간 업데이트
            self.last_analysis_time = datetime.now()
            
            logger.info("✅ 차트 패턴 분석 완료")
            return result_dict
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 실패: {e}")
            logger.error(f"   응답 텍스트: {response_text[:200]}...")
            return self._get_default_chart_analysis()
        except Exception as e:
            logger.error(f"❌ 차트 패턴 분석 실패: {e}")
            return self._get_default_chart_analysis()
    
    def _get_default_chart_analysis(self) -> Dict[str, Any]:
        """기본 차트 분석 결과 (Gemini API 사용 불가 시)"""
        return {
            'success': False,
            'analysis': {
                'patterns': [],
                'trend': 'UNKNOWN',
                'support_level': 0,
                'resistance_level': 0,
                'buy_signal_strength': 0.0,
                'sell_signal_strength': 0.0,
                'confidence': 0.0,
                'recommendation': 'HOLD',
                'reasoning': 'Gemini Vision API 사용 불가'
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_visual_signal_weight(
        self,
        chart_analysis: Dict[str, Any],
        current_analysis: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        시각적 신호를 신호 가중치로 변환
        
        Args:
            chart_analysis: 차트 분석 결과
            current_analysis: 현재 분석 결과
        
        Returns:
            신호 가중치 딕셔너리
        """
        try:
            analysis = chart_analysis.get('analysis', {})
            
            # 시각적 신호 강도
            buy_strength = analysis.get('buy_signal_strength', 0.0)
            sell_strength = analysis.get('sell_signal_strength', 0.0)
            visual_confidence = analysis.get('confidence', 0.0)
            
            # 이론 신호와 융합
            fusion_signal = current_analysis.get('fusion_signal', 'HOLD')
            fusion_confidence = current_analysis.get('confidence', 0.5)
            
            # 가중치 계산
            # 시각적 신호와 이론 신호가 일치하면 가중치 증가
            if fusion_signal == 'BUY' and buy_strength > 0.5:
                signal_weight = 1.0 + (buy_strength * 0.2)  # 최대 20% 증가
            elif fusion_signal == 'SELL' and sell_strength > 0.5:
                signal_weight = 1.0 + (sell_strength * 0.2)  # 최대 20% 증가
            elif fusion_signal == 'HOLD':
                signal_weight = 1.0
            else:
                # 신호 불일치 시 가중치 감소
                signal_weight = 0.8
            
            # 신뢰도 보정
            confidence_boost = (visual_confidence - 0.5) * 0.1  # 최대 ±5%
            
            return {
                'signal_weight': signal_weight,
                'confidence_boost': confidence_boost,
                'visual_confidence': visual_confidence,
                'buy_strength': buy_strength,
                'sell_strength': sell_strength
            }
            
        except Exception as e:
            logger.error(f"❌ 시각적 신호 가중치 계산 실패: {e}")
            return {
                'signal_weight': 1.0,
                'confidence_boost': 0.0,
                'visual_confidence': 0.0,
                'buy_strength': 0.0,
                'sell_strength': 0.0
            }

