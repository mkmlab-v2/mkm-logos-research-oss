#!/usr/bin/env python3
"""
한국 주식 시장 데이터 수집 클라이언트

네이버 파이낸스 API 또는 한국투자증권 API를 통한 주식 데이터 수집
"""
import sys
import os
from pathlib import Path
from typing import Dict, Optional, Any, List
import pandas as pd
import requests
import logging
from datetime import datetime, timedelta
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KoreanStockClient:
    """
    한국 주식 시장 데이터 수집 클라이언트
    
    데이터 소스:
    - 네이버 파이낸스 (기본값, 무료)
    - 한국투자증권 Open API (선택적, 실전매매용)
    """
    
    def __init__(
        self,
        use_kis_api: bool = False,  # 한국투자증권 API 사용 여부
        kis_api_key: Optional[str] = None,
        kis_api_secret: Optional[str] = None
    ):
        """
        Args:
            use_kis_api: 한국투자증권 API 사용 여부
            kis_api_key: 한국투자증권 API 키 (선택적)
            kis_api_secret: 한국투자증권 API 시크릿 (선택적)
        """
        self.use_kis_api = use_kis_api
        self.kis_api_key = kis_api_key
        self.kis_api_secret = kis_api_secret
        
        # 네이버 파이낸스 기본 URL
        self.naver_finance_base = "https://finance.naver.com"
        
        logger.info(f"✅ 한국 주식 클라이언트 초기화 완료 (KIS API: {use_kis_api})")
    
    def get_current_price(self, symbol: str) -> float:
        """
        현재 주가 조회
        
        Args:
            symbol: 종목 코드 (예: "005930" = 삼성전자)
        
        Returns:
            현재 주가
        """
        try:
            if self.use_kis_api and self.kis_api_key:
                return self._get_price_from_kis(symbol)
            else:
                return self._get_price_from_naver(symbol)
        except Exception as e:
            logger.error(f"❌ 현재 주가 조회 실패 ({symbol}): {e}")
            return 0.0
    
    def _get_price_from_naver(self, symbol: str) -> float:
        """네이버 파이낸스에서 현재 주가 조회"""
        try:
            url = f"{self.naver_finance_base}/item/main.naver?code={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"⚠️ 네이버 파이낸스 응답 실패: {response.status_code}")
                return 0.0
            
                # HTML 파싱
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 현재가 추출 (네이버 파이낸스 구조)
                    no_today = soup.find('p', class_='no_today')
                    if no_today:
                        blind = no_today.find('span', class_='blind')
                        if blind:
                            price_str = blind.text.replace(',', '')
                            return float(price_str)
                    
                    # Fallback: 다른 패턴 시도
                    import re
                    price_pattern = r'<p class="no_today">.*?<span class="blind">([0-9,]+)</span>'
                    match = re.search(price_pattern, response.text)
                    if match:
                        price_str = match.group(1).replace(',', '')
                        return float(price_str)
                    
                    logger.warning(f"⚠️ 가격 패턴을 찾을 수 없습니다: {symbol}")
                    return 0.0
                except ImportError:
                    logger.warning("⚠️ BeautifulSoup을 설치하세요: pip install beautifulsoup4")
                    return 0.0
                
        except Exception as e:
            logger.error(f"❌ 네이버 파이낸스 조회 실패: {e}")
            return 0.0
    
    def _get_price_from_kis(self, symbol: str) -> float:
        """한국투자증권 API에서 현재 주가 조회"""
        try:
            # 한국투자증권 API 구현 (향후 추가)
            # 현재는 네이버 파이낸스 사용
            logger.warning("⚠️ 한국투자증권 API는 아직 구현되지 않았습니다. 네이버 파이낸스 사용")
            return self._get_price_from_naver(symbol)
        except Exception as e:
            logger.error(f"❌ 한국투자증권 API 조회 실패: {e}")
            return 0.0
    
    def get_klines(
        self,
        symbol: str,
        interval: str = "1d",  # "1d", "1w", "1m"
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        주식 차트 데이터 조회 (OHLCV)
        
        Args:
            symbol: 종목 코드
            interval: 간격 ("1d", "1w", "1m")
            limit: 조회 개수
        
        Returns:
            OHLCV 데이터 리스트
        """
        try:
            if self.use_kis_api and self.kis_api_key:
                return self._get_klines_from_kis(symbol, interval, limit)
            else:
                return self._get_klines_from_naver(symbol, interval, limit)
        except Exception as e:
            logger.error(f"❌ 차트 데이터 조회 실패 ({symbol}): {e}")
            return []
    
    def _get_klines_from_naver(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """네이버 파이낸스에서 차트 데이터 조회"""
        try:
            # 네이버 파이낸스 차트 API
            url = f"{self.naver_finance_base}/item/sise_day.naver"
            params = {
                'code': symbol,
                'page': 1
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            all_data = []
            page = 1
            max_pages = (limit // 20) + 1  # 한 페이지당 약 20개
            
            while len(all_data) < limit and page <= max_pages:
                params['page'] = page
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    break
                
                # HTML 파싱 (간단한 방법)
                # 실제로는 BeautifulSoup을 사용하는 것이 좋지만, 간단하게 처리
                import re
                from bs4 import BeautifulSoup
                
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', class_='type_2')
                
                if not table:
                    break
                
                rows = table.find_all('tr')[2:]  # 헤더 2줄 제외
                
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue
                    
                    try:
                        date_str = cols[0].text.strip()
                        close = float(cols[1].text.strip().replace(',', ''))
                        change = cols[2].text.strip()
                        change_rate = float(cols[3].text.strip().replace('%', '').replace(',', ''))
                        open_price = float(cols[4].text.strip().replace(',', ''))
                        high = float(cols[5].text.strip().replace(',', ''))
                        low = float(cols[6].text.strip().replace(',', ''))
                        volume = float(cols[7].text.strip().replace(',', ''))
                        
                        # 날짜 파싱
                        date_obj = datetime.strptime(date_str, '%Y.%m.%d')
                        timestamp = int(date_obj.timestamp() * 1000)
                        
                        all_data.append({
                            'timestamp': timestamp,
                            'open': open_price,
                            'high': high,
                            'low': low,
                            'close': close,
                            'volume': volume,
                            'change': change,
                            'change_rate': change_rate
                        })
                        
                        if len(all_data) >= limit:
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ 행 파싱 실패: {e}")
                        continue
                
                page += 1
                time.sleep(0.5)  # API 부하 방지
            
            # 최신순으로 정렬
            all_data.sort(key=lambda x: x['timestamp'], reverse=True)
            return all_data[:limit]
            
        except Exception as e:
            logger.error(f"❌ 네이버 파이낸스 차트 조회 실패: {e}")
            return []
    
    def _get_klines_from_kis(self, symbol: str, interval: str, limit: int) -> List[Dict[str, Any]]:
        """한국투자증권 API에서 차트 데이터 조회"""
        try:
            # 한국투자증권 API 구현 (향후 추가)
            logger.warning("⚠️ 한국투자증권 API는 아직 구현되지 않았습니다. 네이버 파이낸스 사용")
            return self._get_klines_from_naver(symbol, interval, limit)
        except Exception as e:
            logger.error(f"❌ 한국투자증권 API 차트 조회 실패: {e}")
            return []
    
    def get_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """
        재무 지표 조회 (PER, PBR 등)
        
        Args:
            symbol: 종목 코드
        
        Returns:
            재무 지표 딕셔너리
        """
        try:
            if self.use_kis_api and self.kis_api_key:
                return self._get_fundamental_from_kis(symbol)
            else:
                return self._get_fundamental_from_naver(symbol)
        except Exception as e:
            logger.error(f"❌ 재무 지표 조회 실패 ({symbol}): {e}")
            return {
                'per': 0.0,
                'pbr': 0.0,
                'market_cap': 0.0,
                'volume': 0.0
            }
    
    def _get_fundamental_from_naver(self, symbol: str) -> Dict[str, Any]:
        """네이버 파이낸스에서 재무 지표 조회"""
        try:
            url = f"{self.naver_finance_base}/item/main.naver?code={symbol}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return {'per': 0.0, 'pbr': 0.0, 'market_cap': 0.0, 'volume': 0.0}
            
            # HTML 파싱
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PER, PBR 추출 (네이버 파이낸스 구조에 따라 조정 필요)
            per = 0.0
            pbr = 0.0
            market_cap = 0.0
            volume = 0.0
            
            # 간단한 추출 로직 (실제로는 더 정교한 파싱 필요)
            # 네이버 파이낸스 구조에 맞게 조정
            try:
                # PER, PBR은 보통 특정 테이블에 있음
                # 여기서는 기본값 반환 (실제 구현 시 BeautifulSoup으로 정확히 파싱)
                pass
            except Exception as e:
                logger.warning(f"⚠️ 재무 지표 파싱 실패: {e}")
            
            return {
                'per': per,
                'pbr': pbr,
                'market_cap': market_cap,
                'volume': volume
            }
            
        except Exception as e:
            logger.error(f"❌ 네이버 파이낸스 재무 지표 조회 실패: {e}")
            return {'per': 0.0, 'pbr': 0.0, 'market_cap': 0.0, 'volume': 0.0}
    
    def _get_fundamental_from_kis(self, symbol: str) -> Dict[str, Any]:
        """한국투자증권 API에서 재무 지표 조회"""
        try:
            # 한국투자증권 API 구현 (향후 추가)
            logger.warning("⚠️ 한국투자증권 API는 아직 구현되지 않았습니다. 네이버 파이낸스 사용")
            return self._get_fundamental_from_naver(symbol)
        except Exception as e:
            logger.error(f"❌ 한국투자증권 API 재무 지표 조회 실패: {e}")
            return {'per': 0.0, 'pbr': 0.0, 'market_cap': 0.0, 'volume': 0.0}
    
    def get_balance(self) -> Dict[str, float]:
        """
        계좌 잔고 조회 (한국투자증권 API 전용)
        
        Returns:
            잔고 정보 딕셔너리
        """
        try:
            if not self.use_kis_api or not self.kis_api_key:
                logger.warning("⚠️ 한국투자증권 API가 활성화되지 않았습니다")
                return {'total': 0.0, 'available': 0.0}
            
            # 한국투자증권 API 구현 (향후 추가)
            return {'total': 0.0, 'available': 0.0}
        except Exception as e:
            logger.error(f"❌ 계좌 잔고 조회 실패: {e}")
            return {'total': 0.0, 'available': 0.0}
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: int,
        price: Optional[float] = None  # None이면 시장가
    ) -> Optional[Dict[str, Any]]:
        """
        주문 실행 (한국투자증권 API 전용)
        
        Args:
            symbol: 종목 코드
            side: 매수/매도 ("BUY" or "SELL")
            quantity: 수량
            price: 가격 (None이면 시장가)
        
        Returns:
            주문 결과 딕셔너리
        """
        try:
            if not self.use_kis_api or not self.kis_api_key:
                logger.warning("⚠️ 한국투자증권 API가 활성화되지 않았습니다")
                return None
            
            # 한국투자증권 API 구현 (향후 추가)
            logger.warning("⚠️ 주문 실행 기능은 아직 구현되지 않았습니다")
            return None
        except Exception as e:
            logger.error(f"❌ 주문 실행 실패: {e}")
            return None

