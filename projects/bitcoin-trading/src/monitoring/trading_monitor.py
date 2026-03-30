#!/usr/bin/env python3
"""
24시간 무중단 모니터링 시스템

장애 복구, 실시간 알림, 로그 관리
"""
import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path
import json

# AlertManager import
try:
    from src.monitoring.alert_manager import AlertManager
    ALERT_MANAGER_AVAILABLE = True
except ImportError:
    ALERT_MANAGER_AVAILABLE = False
    AlertManager = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingMonitor:
    """
    24시간 무중단 모니터링 시스템
    
    기능:
    - 실시간 상태 모니터링
    - 장애 감지 및 자동 복구
    - 알림 시스템
    - 로그 관리
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        check_interval: int = 60,  # 60초마다 체크
        enable_telegram: bool = True,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None
    ):
        """
        Args:
            log_dir: 로그 디렉토리 (None이면 프로젝트/logs)
            check_interval: 체크 간격 (초)
            enable_telegram: Telegram 알림 활성화 여부
            telegram_bot_token: Telegram 봇 토큰 (환경 변수 대체)
            telegram_chat_id: Telegram 채팅 ID (환경 변수 대체)
        """
        self.log_dir = Path(log_dir) if log_dir else Path(__file__).resolve().parent.parent.parent / "logs"
        self.check_interval = check_interval
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # AlertManager 초기화
        if ALERT_MANAGER_AVAILABLE:
            self.alert_manager = AlertManager(
                enable_telegram=enable_telegram,
                telegram_bot_token=telegram_bot_token,
                telegram_chat_id=telegram_chat_id
            )
        else:
            self.alert_manager = None
            logger.warning("⚠️ AlertManager 사용 불가 (Telegram 알림 비활성화)")
        
        # 상태 추적
        self.status = {
            'last_check': None,
            'last_trade': None,
            'error_count': 0,
            'success_count': 0,
            'is_running': False
        }
        
        # 상태 파일 경로
        self.status_file = self.log_dir / "trading_status.json"
    
    def save_status(self):
        """상태 저장"""
        try:
            self.status['last_check'] = datetime.now().isoformat()
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ 상태 저장 실패: {e}")
    
    def load_status(self) -> Dict[str, Any]:
        """상태 로드"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ 상태 로드 실패: {e}")
        return self.status
    
    def log_trade(self, trade_info: Dict[str, Any]):
        """거래 로그 기록 및 Telegram 알림"""
        try:
            log_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(trade_info, ensure_ascii=False) + '\n')
            
            self.status['last_trade'] = datetime.now().isoformat()
            self.status['success_count'] += 1
            self.save_status()
            
            # Telegram 알림 전송
            if self.alert_manager:
                side = trade_info.get('side', 'UNKNOWN')
                symbol = trade_info.get('symbol', 'UNKNOWN')
                quantity = trade_info.get('quantity', 0.0)
                price = trade_info.get('price', 0.0)
                pnl = trade_info.get('pnl')
                
                asyncio.create_task(
                    self.alert_manager.alert_trade_executed(
                        side=side,
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        pnl=pnl
                    )
                )
        except Exception as e:
            logger.error(f"❌ 거래 로그 기록 실패: {e}")
    
    def log_error(self, error_info: Dict[str, Any]):
        """에러 로그 기록 및 Telegram 알림"""
        try:
            log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, ensure_ascii=False) + '\n')
            
            self.status['error_count'] += 1
            self.save_status()
            
            # Telegram 알림 전송
            if self.alert_manager:
                error_message = error_info.get('message', '알 수 없는 오류')
                error_detail = error_info.get('error', str(error_info))
                
                asyncio.create_task(
                    self.alert_manager.alert_system_status(
                        status="ERROR",
                        message=error_message,
                        error_detail=error_detail
                    )
                )
        except Exception as e:
            logger.error(f"❌ 에러 로그 기록 실패: {e}")
    
    def check_health(self) -> bool:
        """시스템 건강 상태 확인"""
        try:
            # 상태 로드
            status = self.load_status()
            
            # 에러 카운트 확인
            if status.get('error_count', 0) > 10:
                logger.warning("⚠️ 에러 카운트가 10회를 초과했습니다.")
                return False
            
            # 마지막 체크 시간 확인
            last_check = status.get('last_check')
            if last_check:
                last_check_time = datetime.fromisoformat(last_check)
                time_diff = (datetime.now() - last_check_time).total_seconds()
                if time_diff > 300:  # 5분 이상 체크 없음
                    logger.warning(f"⚠️ 마지막 체크로부터 {time_diff:.0f}초 경과")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"❌ 건강 상태 확인 실패: {e}")
            return False
    
    async def monitor_loop(self, trading_system):
        """모니터링 루프"""
        logger.info("🚀 모니터링 시스템 시작")
        self.status['is_running'] = True
        self.save_status()
        
        # 시작 알림
        if self.alert_manager:
            await self.alert_manager.alert_system_status(
                status="STARTED",
                message="비트코인 24시간 매매 시스템이 시작되었습니다."
            )
        
        while self.status['is_running']:
            try:
                # 건강 상태 확인
                if not self.check_health():
                    logger.warning("⚠️ 시스템 건강 상태 불량, 복구 시도...")
                    
                    # Telegram 알림
                    if self.alert_manager:
                        await self.alert_manager.alert_system_status(
                            status="ERROR",
                            message="시스템 건강 상태 불량 감지, 복구 시도 중..."
                        )
                    
                    # 복구 로직 (재시작 등)
                    # TODO: 실제 복구 로직 구현
                
                # 상태 저장
                self.save_status()
                
                # 대기
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("⏹️ 모니터링 중단")
                break
            except Exception as e:
                logger.error(f"❌ 모니터링 루프 오류: {e}")
                
                # Telegram 알림
                if self.alert_manager:
                    await self.alert_manager.alert_system_status(
                        status="ERROR",
                        message="모니터링 루프 오류 발생",
                        error_detail=str(e)
                    )
                
                await asyncio.sleep(self.check_interval)
        
        self.status['is_running'] = False
        self.save_status()
        
        # 중지 알림
        if self.alert_manager:
            await self.alert_manager.alert_system_status(
                status="STOPPED",
                message="비트코인 24시간 매매 시스템이 중지되었습니다."
            )
    
    def stop(self):
        """모니터링 중지"""
        self.status['is_running'] = False
        self.save_status()
        logger.info("⏹️ 모니터링 중지")


