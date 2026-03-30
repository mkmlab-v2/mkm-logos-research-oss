#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VPS 헬스 모니터 및 자동 재시작 시스템

목적: 비트코인 자동매매 시스템의 24시간 무중단 운영 보장
- 자동 헬스체크
- 오류 감지 및 자동 복구
- MCP 브릿지 안정성 모니터링
- PM2 프로세스 관리

작성일: 2026-01-30
상태: ✅ 구축 완료
"""

import sys
import os
import json
import asyncio
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import signal

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

# Alert Manager import
try:
    from src.monitoring.alert_manager import AlertManager
    ALERT_MANAGER_AVAILABLE = True
except ImportError:
    ALERT_MANAGER_AVAILABLE = False
    AlertManager = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('projects/bitcoin-trading/logs/health_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VPSHealthMonitor:
    """
    VPS 헬스 모니터 및 자동 재시작 시스템
    
    기능:
    1. 주기적 헬스체크 (프로세스, 메모리, 디스크, 네트워크)
    2. 오류 감지 및 자동 복구
    3. MCP 브릿지 안정성 모니터링
    4. PM2 프로세스 관리
    """
    
    def __init__(
        self,
        check_interval: int = 60,  # 헬스체크 간격 (초)
        max_restart_attempts: int = 5,  # 최대 재시작 시도 횟수
        restart_delay: int = 30,  # 재시작 대기 시간 (초)
        pm2_process_name: str = "bitcoin-trading-24h-daemon"  # PM2 프로세스 이름 통일
    ):
        """
        Args:
            check_interval: 헬스체크 간격 (초, 기본값: 60)
            max_restart_attempts: 최대 재시작 시도 횟수 (기본값: 5)
            restart_delay: 재시작 대기 시간 (초, 기본값: 30)
            pm2_process_name: PM2 프로세스 이름 (기본값: "bitcoin-trading")
        """
        self.check_interval = check_interval
        self.max_restart_attempts = max_restart_attempts
        self.restart_delay = restart_delay
        self.pm2_process_name = pm2_process_name
        
        # 상태 추적
        self.is_running = False
        self.restart_count = 0
        self.last_restart_time: Optional[datetime] = None
        self.health_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # 헬스체크 결과
        self.last_health_check: Optional[Dict[str, Any]] = None
        
        # Alert Manager 초기화 (중요 이벤트 알림용)
        self.alert_manager = None
        if ALERT_MANAGER_AVAILABLE:
            try:
                self.alert_manager = AlertManager()
                logger.info("✅ Alert Manager 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Alert Manager 초기화 실패: {e}")
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"✅ VPS Health Monitor 초기화 완료")
        logger.info(f"   - 헬스체크 간격: {check_interval}초")
        logger.info(f"   - 최대 재시작 시도: {max_restart_attempts}회")
        logger.info(f"   - PM2 프로세스 이름: {pm2_process_name}")
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (종료 신호 처리)"""
        logger.info(f"📡 종료 시그널 수신: {signum}")
        self.is_running = False
    
    async def check_pm2_process(self) -> Dict[str, Any]:
        """
        PM2 프로세스 상태 확인
        
        Returns:
            프로세스 상태 딕셔너리
        """
        try:
            # PM2 상태 확인
            result = subprocess.run(
                ["pm2", "jlist"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"PM2 상태 확인 실패: {result.stderr}",
                    "is_running": False
                }
            
            # JSON 파싱
            pm2_list = json.loads(result.stdout)
            
            # 프로세스 찾기
            process = None
            for proc in pm2_list:
                if proc.get("name") == self.pm2_process_name:
                    process = proc
                    break
            
            if process is None:
                return {
                    "status": "not_found",
                    "message": f"PM2 프로세스 '{self.pm2_process_name}'를 찾을 수 없습니다",
                    "is_running": False
                }
            
            # 상태 확인
            pm2_status = process.get("pm2_env", {}).get("status", "unknown")
            is_running = pm2_status == "online"
            
            # 메모리 사용량
            memory_usage = process.get("monit", {}).get("memory", 0)
            
            # CPU 사용량
            cpu_usage = process.get("monit", {}).get("cpu", 0)
            
            # 재시작 횟수
            restart_count = process.get("pm2_env", {}).get("restart_time", 0)
            
            # 업타임
            uptime = process.get("pm2_env", {}).get("pm_uptime", 0)
            
            return {
                "status": "ok",
                "is_running": is_running,
                "pm2_status": pm2_status,
                "memory_usage_mb": memory_usage / 1024 / 1024 if memory_usage > 0 else 0,
                "cpu_usage_percent": cpu_usage,
                "restart_count": restart_count,
                "uptime_seconds": uptime,
                "pid": process.get("pid")
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "PM2 상태 확인 타임아웃",
                "is_running": False
            }
        except Exception as e:
            logger.error(f"❌ PM2 프로세스 확인 실패: {e}")
            return {
                "status": "error",
                "message": str(e),
                "is_running": False
            }
    
    async def check_mcp_bridge(self) -> Dict[str, Any]:
        """
        MCP 브릿지 안정성 확인
        
        Returns:
            MCP 브릿지 상태 딕셔너리
        """
        try:
            # Strategic Meeting Bridge import 시도
            from src.integration.strategic_meeting_bridge import StrategicMeetingBridge
            
            # 브릿지 초기화 테스트
            bridge = StrategicMeetingBridge(use_character_committee=False)  # 테스트용으로 비활성화
            
            return {
                "status": "ok",
                "bridge_available": True,
                "message": "MCP 브릿지 정상"
            }
        except ImportError as e:
            return {
                "status": "warning",
                "bridge_available": False,
                "message": f"MCP 브릿지 import 실패: {e}"
            }
        except Exception as e:
            return {
                "status": "error",
                "bridge_available": False,
                "message": f"MCP 브릿지 확인 실패: {e}"
            }
    
    async def check_disk_space(self) -> Dict[str, Any]:
        """
        디스크 공간 확인 (로그 디렉토리 포함)
        
        Returns:
            디스크 공간 상태 딕셔너리
        """
        try:
            import psutil
            from pathlib import Path
            
            # 루트 디스크 사용량
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / 1024 / 1024 / 1024
            
            # 로그 디렉토리 크기 확인
            log_dir = Path('/opt/bitcoin-trading/logs')
            log_size = 0
            log_size_gb = 0.0
            if log_dir.exists():
                for log_file in log_dir.rglob('*'):
                    if log_file.is_file():
                        log_size += log_file.stat().st_size
                log_size_gb = log_size / 1024 / 1024 / 1024
            
            # 경고: 디스크 사용량 90% 이상 또는 로그 크기 10GB 이상
            if disk_percent >= 90:
                logger.error(f"🚨 디스크 공간 부족: {disk_percent:.1f}% 사용 중")
                # 오래된 로그 삭제
                await self._cleanup_old_logs()
            elif disk_percent >= 80:
                logger.warning(f"⚠️ 디스크 사용량 높음: {disk_percent:.1f}%")
            
            if log_size_gb >= 10.0:
                logger.warning(f"⚠️ 로그 크기 초과: {log_size_gb:.2f}GB, 정리 필요")
                await self._cleanup_old_logs()
            
            return {
                "status": "ok",
                "disk_percent": disk_percent,
                "disk_free_gb": disk_free_gb,
                "log_size_gb": log_size_gb,
                "warning": disk_percent >= 80,
                "critical": disk_percent >= 90
            }
        except Exception as e:
            logger.error(f"❌ 디스크 공간 확인 실패: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _cleanup_old_logs(self, days: int = 7, max_size_gb: float = 10.0):
        """오래된 로그 파일 삭제"""
        try:
            from pathlib import Path
            from datetime import datetime, timedelta
            
            log_dir = Path('/opt/bitcoin-trading/logs')
            if not log_dir.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=days)
            total_size = 0
            deleted_count = 0
            
            # 오래된 로그 파일 삭제
            for log_file in log_dir.rglob('*.log*'):
                if log_file.is_file():
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_size = log_file.stat().st_size
                        log_file.unlink()
                        deleted_count += 1
                        logger.info(f"🗑️ 오래된 로그 삭제: {log_file.name} ({file_size / 1024 / 1024:.1f}MB)")
                    else:
                        total_size += log_file.stat().st_size
            
            # 크기 제한 초과 시 오래된 파일부터 삭제
            total_size_gb = total_size / 1024 / 1024 / 1024
            if total_size_gb > max_size_gb:
                log_files = sorted(
                    [f for f in log_dir.rglob('*.log*') if f.is_file()],
                    key=lambda f: f.stat().st_mtime
                )
                for log_file in log_files:
                    if total_size_gb <= max_size_gb:
                        break
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    total_size_gb -= file_size / 1024 / 1024 / 1024
                    deleted_count += 1
                    logger.info(f"🗑️ 로그 파일 삭제 (크기 제한): {log_file.name} ({file_size / 1024 / 1024:.1f}MB)")
            
            if deleted_count > 0:
                logger.info(f"✅ 로그 정리 완료: {deleted_count}개 파일 삭제")
        except Exception as e:
            logger.error(f"❌ 로그 정리 실패: {e}")
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """
        시스템 리소스 확인 (메모리, 디스크, CPU)
        
        Returns:
            시스템 리소스 상태 딕셔너리
        """
        try:
            import psutil
            
            # 메모리 사용량
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / 1024 / 1024 / 1024
            
            # 디스크 사용량 (디스크 공간 확인 포함)
            disk_status = await self.check_disk_space()
            
            # CPU 사용량
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "status": "ok",
                "memory": {
                    "percent": memory_percent,
                    "available_gb": memory_available_gb,
                    "warning": memory_percent > 80,
                    "critical": memory_percent > 90
                },
                "disk": disk_status if disk_status.get("status") == "ok" else {
                    "percent": 0,
                    "free_gb": 0,
                    "log_size_gb": 0,
                    "warning": False,
                    "critical": False
                },
                "cpu": {
                    "percent": cpu_percent,
                    "warning": cpu_percent > 80,
                    "critical": cpu_percent > 90
                }
            }
        except ImportError:
            logger.warning("⚠️ psutil 미설치, 시스템 리소스 확인 불가")
            return {
                "status": "unavailable",
                "message": "psutil 미설치"
            }
        except Exception as e:
            logger.error(f"❌ 시스템 리소스 확인 실패: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """
        전체 헬스체크 수행
        
        Returns:
            헬스체크 결과 딕셔너리
        """
        try:
            timestamp = datetime.now()
            
            # 1. PM2 프로세스 확인
            pm2_status = await self.check_pm2_process()
            
            # 2. MCP 브릿지 확인
            mcp_status = await self.check_mcp_bridge()
            
            # 3. 시스템 리소스 확인
            system_status = await self.check_system_resources()
            
            # 전체 상태 판단
            is_healthy = (
                pm2_status.get("is_running", False) and
                pm2_status.get("status") == "ok"
            )
            
            # 경고 사항 수집
            warnings = []
            if not pm2_status.get("is_running", False):
                warnings.append("PM2 프로세스가 실행 중이 아닙니다")
            if pm2_status.get("restart_count", 0) > 10:
                warnings.append(f"PM2 재시작 횟수가 많습니다: {pm2_status.get('restart_count')}")
            if system_status.get("status") == "ok":
                if system_status.get("memory", {}).get("warning"):
                    memory_percent = system_status.get("memory", {}).get("percent", 0)
                    warnings.append(f"메모리 사용량 높음: {memory_percent:.1f}%")
                    # 메모리 경고 알림
                    if self.alert_manager and memory_percent > 80:
                        await self.alert_manager.alert_vps_health(
                            health_status="WARNING" if memory_percent < 90 else "CRITICAL",
                            component="MEMORY",
                            message=f"메모리 사용량이 높습니다: {memory_percent:.1f}%",
                            metrics=system_status.get("memory", {})
                        )
                if system_status.get("disk", {}).get("warning"):
                    disk_percent = system_status.get("disk", {}).get("percent", 0)
                    warnings.append(f"디스크 사용량 높음: {disk_percent:.1f}%")
                    # 디스크 경고 알림
                    if self.alert_manager and disk_percent > 80:
                        await self.alert_manager.alert_vps_health(
                            health_status="WARNING" if disk_percent < 90 else "CRITICAL",
                            component="DISK",
                            message=f"디스크 사용량이 높습니다: {disk_percent:.1f}%",
                            metrics=system_status.get("disk", {})
                        )
                if system_status.get("cpu", {}).get("warning"):
                    cpu_percent = system_status.get("cpu", {}).get("percent", 0)
                    warnings.append(f"CPU 사용량 높음: {cpu_percent:.1f}%")
                    # CPU 경고 알림
                    if self.alert_manager and cpu_percent > 80:
                        await self.alert_manager.alert_vps_health(
                            health_status="WARNING" if cpu_percent < 90 else "CRITICAL",
                            component="CPU",
                            message=f"CPU 사용량이 높습니다: {cpu_percent:.1f}%",
                            metrics=system_status.get("cpu", {})
                        )
            
            health_result = {
                "timestamp": timestamp.isoformat(),
                "is_healthy": is_healthy,
                "pm2": pm2_status,
                "mcp_bridge": mcp_status,
                "system": system_status,
                "warnings": warnings
            }
            
            # 히스토리 저장
            self.health_history.append(health_result)
            if len(self.health_history) > self.max_history_size:
                self.health_history = self.health_history[-self.max_history_size:]
            
            self.last_health_check = health_result
            
            return health_result
            
        except Exception as e:
            logger.error(f"❌ 헬스체크 실패: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "is_healthy": False,
                "error": str(e)
            }
    
    async def restart_pm2_process(self) -> bool:
        """
        PM2 프로세스 재시작
        
        Returns:
            재시작 성공 여부
        """
        try:
            logger.info(f"🔄 PM2 프로세스 재시작 시도: {self.pm2_process_name}")
            
            # 재시작 횟수 확인
            if self.restart_count >= self.max_restart_attempts:
                logger.error(f"❌ 최대 재시작 시도 횟수({self.max_restart_attempts}회) 초과")
                return False
            
            # 마지막 재시작 시간 확인 (너무 빈번한 재시작 방지)
            if self.last_restart_time:
                time_since_last = datetime.now() - self.last_restart_time
                if time_since_last < timedelta(minutes=5):
                    logger.warning(f"⚠️ 재시작이 너무 빈번합니다. 대기 중... ({time_since_last.total_seconds():.0f}초 전)")
                    return False
            
            # PM2 재시작
            result = subprocess.run(
                ["pm2", "restart", self.pm2_process_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.restart_count += 1
                self.last_restart_time = datetime.now()
                logger.info(f"✅ PM2 프로세스 재시작 성공 (재시작 횟수: {self.restart_count}/{self.max_restart_attempts})")
                return True
            else:
                logger.error(f"❌ PM2 프로세스 재시작 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ PM2 재시작 타임아웃")
            return False
        except Exception as e:
            logger.error(f"❌ PM2 재시작 실패: {e}")
            return False
    
    async def start_pm2_process(self) -> bool:
        """
        PM2 프로세스 시작 (프로세스가 없을 때)
        
        Returns:
            시작 성공 여부
        """
        try:
            logger.info(f"🚀 PM2 프로세스 시작 시도: {self.pm2_process_name}")
            
            # 프로세스 시작 (ecosystem.config.js 사용)
            result = subprocess.run(
                ["pm2", "start", "ecosystem.config.js", "--only", self.pm2_process_name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(workspace_root / "projects" / "bitcoin-trading")
            )
            
            if result.returncode == 0:
                logger.info(f"✅ PM2 프로세스 시작 성공")
                return True
            else:
                logger.error(f"❌ PM2 프로세스 시작 실패: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ PM2 시작 타임아웃")
            return False
        except Exception as e:
            logger.error(f"❌ PM2 시작 실패: {e}")
            return False
    
    async def auto_recover(self, health_result: Dict[str, Any]) -> bool:
        """
        자동 복구 시도
        
        Args:
            health_result: 헬스체크 결과
        
        Returns:
            복구 성공 여부
        """
        try:
            pm2_status = health_result.get("pm2", {})
            
            # PM2 프로세스가 실행 중이 아닌 경우
            if not pm2_status.get("is_running", False):
                logger.warning("⚠️ PM2 프로세스가 실행 중이 아닙니다. 복구 시도...")
                
                # 프로세스 상태 확인
                if pm2_status.get("status") == "not_found":
                    # 프로세스가 없으면 시작
                    return await self.start_pm2_process()
                else:
                    # 프로세스가 있으면 재시작
                    return await self.restart_pm2_process()
            
            # PM2 프로세스가 있지만 상태가 이상한 경우
            if pm2_status.get("status") != "ok":
                logger.warning(f"⚠️ PM2 프로세스 상태 이상: {pm2_status.get('status')}. 재시작 시도...")
                return await self.restart_pm2_process()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 자동 복구 실패: {e}")
            return False
    
    async def monitor_loop(self):
        """헬스체크 루프 (무한 반복)"""
        self.is_running = True
        logger.info("🏥 VPS 헬스 모니터 시작")
        
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        try:
            while self.is_running:
                try:
                    # 헬스체크 수행
                    health_result = await self.perform_health_check()
                    
                    # 상태 로깅
                    if health_result.get("is_healthy"):
                        consecutive_failures = 0
                        logger.info("✅ 헬스체크 통과")
                    else:
                        consecutive_failures += 1
                        logger.warning(f"⚠️ 헬스체크 실패 (연속 {consecutive_failures}회)")
                        
                        # 경고 사항 출력
                        warnings = health_result.get("warnings", [])
                        for warning in warnings:
                            logger.warning(f"   - {warning}")
                        
                        # 연속 실패 시 자동 복구 시도
                        if consecutive_failures >= max_consecutive_failures:
                            logger.warning("⚠️ 연속 실패 횟수 초과. 자동 복구 시도...")
                            
                            # 중요 이벤트 알림
                            if self.alert_manager:
                                await self.alert_manager.alert_vps_health(
                                    health_status="CRITICAL",
                                    component="PM2",
                                    message=f"연속 {consecutive_failures}회 헬스체크 실패. 자동 복구를 시도합니다.",
                                    metrics={
                                        "consecutive_failures": consecutive_failures,
                                        "max_consecutive_failures": max_consecutive_failures,
                                        "warnings": health_result.get("warnings", [])
                                    }
                                )
                            
                            recovery_success = await self.auto_recover(health_result)
                            
                            if recovery_success:
                                logger.info("✅ 자동 복구 성공")
                                consecutive_failures = 0
                                
                                # 복구 성공 알림
                                if self.alert_manager:
                                    await self.alert_manager.alert_vps_health(
                                        health_status="HEALTHY",
                                        component="PM2",
                                        message="자동 복구 성공. 시스템이 정상 작동 중입니다.",
                                        metrics={"recovery_success": True}
                                    )
                            else:
                                logger.error("❌ 자동 복구 실패")
                                
                                # 복구 실패 알림
                                if self.alert_manager:
                                    await self.alert_manager.alert_vps_health(
                                        health_status="CRITICAL",
                                        component="PM2",
                                        message="자동 복구 실패. 수동 개입이 필요할 수 있습니다.",
                                        metrics={"recovery_success": False}
                                    )
                    
                    # 대기
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"❌ 헬스체크 루프 오류: {e}")
                    await asyncio.sleep(self.check_interval)
                    
        except KeyboardInterrupt:
            logger.info("📡 종료 신호 수신")
        finally:
            self.is_running = False
            logger.info("🏥 VPS 헬스 모니터 종료")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """헬스체크 요약 정보 반환"""
        if not self.last_health_check:
            return {
                "status": "unknown",
                "message": "헬스체크가 아직 수행되지 않았습니다"
            }
        
        return {
            "status": "healthy" if self.last_health_check.get("is_healthy") else "unhealthy",
            "last_check": self.last_health_check.get("timestamp"),
            "pm2_running": self.last_health_check.get("pm2", {}).get("is_running", False),
            "restart_count": self.restart_count,
            "warnings": self.last_health_check.get("warnings", [])
        }


async def main():
    """메인 함수 (독립 실행용)"""
    monitor = VPSHealthMonitor(
        check_interval=60,  # 1분마다 체크
        max_restart_attempts=5,
        restart_delay=30,
        pm2_process_name="bitcoin-trading"
    )
    
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())

