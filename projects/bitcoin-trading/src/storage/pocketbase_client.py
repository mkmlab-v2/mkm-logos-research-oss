#!/usr/bin/env python3
"""
PocketBase 클라이언트

비트코인 트레이딩 봇의 거래 기록을 PocketBase에 저장
"""
import os
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class PocketBaseClient:
    """
    PocketBase 클라이언트
    
    거래 기록을 PocketBase에 저장하고 실시간 구독 지원
    """
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Args:
            base_url: PocketBase 서버 URL (기본값: 환경 변수에서 로드)
        """
        self.base_url = base_url or os.getenv(
            "POCKETBASE_URL",
            "http://148.230.97.246:8090"  # VPS PocketBase 기본 URL
        )
        self.api_url = f"{self.base_url}/api"
        self.collection_name = "trades"
        
        # 인증 토큰 (필요 시)
        self.auth_token = os.getenv("POCKETBASE_AUTH_TOKEN")
        
        logger.info(f"📦 PocketBase 클라이언트 초기화: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """요청 헤더 생성"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def save_trade(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        price: float,
        signal_confidence: float,
        risk_mode: str = "normal",  # "defensive", "aggressive", "normal"
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        거래 기록 저장
        
        Args:
            symbol: 거래 심볼 (예: "BTCUSDT")
            side: 거래 방향 ("BUY" or "SELL")
            quantity: 거래 수량
            price: 거래 가격
            signal_confidence: 신호 신뢰도 (0-1)
            risk_mode: 리스크 모드 ("defensive", "aggressive", "normal")
            stop_loss_pct: 손절 비율 (예: 0.02 = -2%)
            take_profit_pct: 익절 비율 (예: 0.04 = +4%)
            metadata: 추가 메타데이터
            
        Returns:
            저장된 레코드 ID 또는 None (실패 시)
        """
        try:
            record_data = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "signal_confidence": signal_confidence,
                "risk_mode": risk_mode,
                "timestamp": datetime.utcnow().isoformat(),
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
                "metadata": metadata or {}
            }
            
            response = requests.post(
                f"{self.api_url}/collections/{self.collection_name}/records",
                json=record_data,
                headers=self._get_headers(),
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                record_id = response.json().get("id")
                logger.info(f"✅ 거래 기록 저장 완료: {side} {quantity} {symbol} @ {price} (ID: {record_id})")
                return record_id
            else:
                logger.error(f"❌ 거래 기록 저장 실패: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ PocketBase 저장 오류: {e}", exc_info=True)
            return None
    
    def update_trade_status(
        self,
        record_id: str,
        status: str,  # "open", "closed", "stopped", "taken"
        realized_pnl: Optional[float] = None,
        close_price: Optional[float] = None
    ) -> bool:
        """
        거래 상태 업데이트
        
        Args:
            record_id: 레코드 ID
            status: 상태 ("open", "closed", "stopped", "taken")
            realized_pnl: 실현 손익 (USDT)
            close_price: 청산 가격
            
        Returns:
            성공 여부
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if realized_pnl is not None:
                update_data["realized_pnl"] = realized_pnl
            if close_price is not None:
                update_data["close_price"] = close_price
            
            response = requests.patch(
                f"{self.api_url}/collections/{self.collection_name}/records/{record_id}",
                json=update_data,
                headers=self._get_headers(),
                timeout=5
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ 거래 상태 업데이트 완료: {record_id} → {status}")
                return True
            else:
                logger.error(f"❌ 거래 상태 업데이트 실패: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ PocketBase 업데이트 오류: {e}", exc_info=True)
            return False
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            response = requests.get(
                f"{self.api_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"⚠️ PocketBase 연결 테스트 실패: {e}")
            return False



