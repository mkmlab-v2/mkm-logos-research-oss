#!/usr/bin/env python3
"""
비트코인 매매 알림 관리자 (Telegram 통합)

기능:
- 거래 알림 (매수/매도)
- 리스크 경고 (Max Drawdown, 일일 손실 한도)
- 시스템 상태 알림 (에러, 복구)
- 성과 리포트 (일일/주간/월간)
"""
import os
import asyncio
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime
from pathlib import Path

try:
    from src.llm.llm_14b_advisory import get_14b_advisory
    LLM_14B_AVAILABLE = True
except ImportError:
    get_14b_advisory = None
    LLM_14B_AVAILABLE = False

try:
    from src.integration.prophecy_sync import load_prophecy_context
    PROPHECY_CONTEXT_AVAILABLE = True
except ImportError:
    load_prophecy_context = None
    PROPHECY_CONTEXT_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertManager:
    """
    비트코인 매매 알림 관리자
    
    Telegram 알림 통합:
    - 거래 실행 알림
    - 리스크 경고
    - 시스템 상태 알림
    - 성과 리포트
    """
    
    def __init__(
        self,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        enable_telegram: bool = True
    ):
        """
        Args:
            telegram_bot_token: Telegram Bot Token (환경 변수에서 자동 로드)
            telegram_chat_id: Telegram Chat ID (환경 변수에서 자동 로드)
            enable_telegram: Telegram 알림 활성화 여부
        """
        # Telegram 설정
        self.telegram_bot_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enable_telegram = enable_telegram and REQUESTS_AVAILABLE
        
        if self.enable_telegram and (not self.telegram_bot_token or not self.telegram_chat_id):
            logger.warning("⚠️ Telegram 환경 변수 없음 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
            logger.warning("⚠️ Telegram 알림 비활성화")
            self.enable_telegram = False
        
        # 알림 이력 저장
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_history_file = Path("projects/bitcoin-trading/logs/alert_history.jsonl")
        self.alert_history_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ Alert Manager 초기화 완료 (Telegram: {'활성화' if self.enable_telegram else '비활성화'})")
    
    async def send_telegram(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Telegram 메시지 전송
        
        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드 (Markdown, HTML)
        
        Returns:
            성공 여부
        """
        if not self.enable_telegram:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            # 비동기 요청
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(url, json=payload, timeout=10)
            )
            response.raise_for_status()
            
            logger.info("✅ Telegram 알림 전송 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ Telegram 알림 전송 실패: {e}")
            return False
    
    async def alert_trade_executed(
        self,
        side: str,  # "BUY" or "SELL"
        symbol: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None
    ):
        """
        거래 실행 알림
        
        Args:
            side: 매수/매도 ("BUY" or "SELL")
            symbol: 거래 심볼
            quantity: 수량
            price: 가격
            pnl: 손익 (있을 경우)
        """
        emoji = "🟢" if side == "BUY" else "🔴"
        pnl_text = f"\n💰 손익: {pnl:+.2f} USDT" if pnl is not None else ""
        
        message = f"""
{emoji} *거래 실행*

*{side}* {symbol}
📊 수량: {quantity:.6f}
💵 가격: ${price:,.2f}{pnl_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self._send_and_log("trade", message, {
            "side": side,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "pnl": pnl
        })
    
    async def alert_risk_warning(
        self,
        warning_type: str,  # "MAX_DRAWDOWN", "DAILY_LOSS_LIMIT", "POSITION_SIZE"
        current_value: float,
        threshold: float,
        message_detail: Optional[str] = None
    ):
        """
        리스크 경고 알림
        
        Args:
            warning_type: 경고 타입
            current_value: 현재 값
            threshold: 임계값
            message_detail: 추가 메시지
        """
        warning_messages = {
            "MAX_DRAWDOWN": "⚠️ *Max Drawdown 경고*",
            "DAILY_LOSS_LIMIT": "🚨 *일일 손실 한도 경고*",
            "POSITION_SIZE": "📊 *포지션 크기 경고*"
        }
        
        title = warning_messages.get(warning_type, "⚠️ *리스크 경고*")
        detail_text = f"\n📝 {message_detail}" if message_detail else ""
        
        message = f"""
{title}

현재 값: {current_value:.2f}%
임계값: {threshold:.2f}%
{detail_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self._send_and_log("risk", message, {
            "warning_type": warning_type,
            "current_value": current_value,
            "threshold": threshold,
            "message_detail": message_detail
        })
    
    async def alert_system_status(
        self,
        status: str,  # "ERROR", "RECOVERED", "STOPPED", "STARTED"
        message: str,
        error_detail: Optional[str] = None
    ):
        """
        시스템 상태 알림
        
        Args:
            status: 상태 ("ERROR", "RECOVERED", "STOPPED", "STARTED")
            message: 메시지
            error_detail: 에러 상세 (있을 경우)
        """
        status_emojis = {
            "ERROR": "❌",
            "RECOVERED": "✅",
            "STOPPED": "⏹️",
            "STARTED": "🚀"
        }
        
        emoji = status_emojis.get(status, "ℹ️")
        error_text = f"\n\n🐛 *에러 상세:*\n```\n{error_detail}\n```" if error_detail else ""
        
        alert_message = f"""
{emoji} *시스템 상태: {status}*

{message}{error_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self._send_and_log("system", alert_message, {
            "status": status,
            "message": message,
            "error_detail": error_detail
        })
    
    async def alert_performance_report(
        self,
        period: str,  # "daily", "weekly", "monthly"
        total_return: float,
        total_trades: int,
        win_rate: float,
        max_drawdown: float,
        sharpe_ratio: Optional[float] = None
    ):
        """
        성과 리포트 알림
        
        Args:
            period: 기간 ("daily", "weekly", "monthly")
            total_return: 총 수익률 (%)
            total_trades: 총 거래 수
            win_rate: 승률 (%)
            max_drawdown: 최대 낙폭 (%)
            sharpe_ratio: 샤프 비율 (있을 경우)
        """
        period_names = {
            "daily": "일일",
            "weekly": "주간",
            "monthly": "월간"
        }
        
        period_name = period_names.get(period, period)
        sharpe_text = f"\n📈 샤프 비율: {sharpe_ratio:.2f}" if sharpe_ratio else ""
        
        message = f"""
📊 *{period_name} 성과 리포트*

💰 총 수익률: {total_return:+.2f}%
📈 총 거래 수: {total_trades}회
🎯 승률: {win_rate:.2f}%
📉 최대 낙폭: {max_drawdown:.2f}%{sharpe_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self._send_and_log("performance", message, {
            "period": period,
            "total_return": total_return,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio
        })
    
    async def _send_and_log(
        self,
        alert_type: str,
        message: str,
        metadata: Dict[str, Any]
    ):
        """
        알림 전송 및 로그 기록
        
        Args:
            alert_type: 알림 타입
            message: 메시지
            metadata: 메타데이터
        """
        # Telegram 전송
        success = await self.send_telegram(message)
        
        # 알림 이력 저장
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "metadata": metadata,
            "telegram_sent": success
        }
        
        self.alert_history.append(alert_record)
        
        # 파일에 저장 (JSONL 형식)
        try:
            with open(self.alert_history_file, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps(alert_record, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"❌ 알림 이력 저장 실패: {e}")
        
        # 최근 1000개만 메모리에 유지
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
    
    async def alert_critical_event(
        self,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "HIGH"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    ):
        """
        중요 이벤트 알림 (Circuit Breaker, 프로세스 재시작 등)
        
        Args:
            event_type: 이벤트 타입 (예: "CIRCUIT_BREAKER_OPEN", "PM2_RESTART", "DISK_FULL")
            message: 메시지
            details: 상세 정보 딕셔너리
            severity: 심각도 ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        """
        severity_emojis = {
            "LOW": "ℹ️",
            "MEDIUM": "⚠️",
            "HIGH": "🚨",
            "CRITICAL": "🔴"
        }
        
        emoji = severity_emojis.get(severity, "⚠️")
        details_text = ""
        if details:
            import json
            details_text = f"\n\n📋 *상세 정보:*\n```json\n{json.dumps(details, ensure_ascii=False, indent=2)}\n```"
        
        alert_message = f"""
{emoji} *중요 이벤트: {event_type}*

{message}{details_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self._send_and_log("critical", alert_message, {
            "event_type": event_type,
            "message": message,
            "details": details,
            "severity": severity
        })
        
        # CRITICAL 이벤트는 로그에도 기록
        if severity == "CRITICAL":
            logger.critical(f"🚨 CRITICAL 이벤트: {event_type} - {message}")
    
    async def alert_vps_health(
        self,
        health_status: str,  # "HEALTHY", "WARNING", "CRITICAL", "DOWN"
        component: str,  # "PM2", "DISK", "MEMORY", "CPU", "API"
        message: str,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        VPS 헬스 상태 알림
        
        Args:
            health_status: 헬스 상태
            component: 컴포넌트 이름
            message: 메시지
            metrics: 메트릭 정보
        """
        status_emojis = {
            "HEALTHY": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "🚨",
            "DOWN": "🔴"
        }
        
        emoji = status_emojis.get(health_status, "ℹ️")
        metrics_text = ""
        if metrics:
            import json
            metrics_text = f"\n\n📊 *메트릭:*\n```json\n{json.dumps(metrics, ensure_ascii=False, indent=2)}\n```"
        
        alert_message = f"""
{emoji} *VPS 헬스 상태: {component}*

상태: *{health_status}*
{message}{metrics_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        await self._send_and_log("vps_health", alert_message, {
            "health_status": health_status,
            "component": component,
            "message": message,
            "metrics": metrics
        })
    
    async def alert_trading_insights(
        self,
        signal: str,
        confidence: float,
        current_price: float,
        indicators: Dict[str, Any],
        apocalypse_insight: Optional[Dict[str, Any]] = None,
        call_path_14b: Optional[Dict[str, Any]] = None,
    ):
        """
        🚀 각종 지표 참조한 통찰 리포트 (신규 추가)
        
        Args:
            signal: 매매 신호 ("BUY", "SELL", "HOLD")
            confidence: 신뢰도 (0.0 ~ 1.0)
            current_price: 현재 가격
            indicators: 각종 지표 정보
                - transfer_entropy: 전이 엔트로피
                - market_regime: 시장 국면
                - compression_ratio: 압축률
                - sentiment: 감성 레이블
                - news_confidence: 뉴스 신뢰도
            apocalypse_insight: 예언 묵시록 통찰 (선택적)
                - collapse_risk: 붕괴 위험도
                - stability: 안정성
                - apocalypse_signal: 묵시록 신호 조정
            call_path_14b: 14B+4D-Native 호출 경로 (get_14b_4d_native_call_path 반환값).
                설정 시 한 문장 14B 제언을 통찰에 추가 (감찰/제언용, 매매 실행 아님).
        """
        signal_emoji = {
            "BUY": "🟢",
            "SELL": "🔴",
            "HOLD": "⏸️"
        }
        emoji = signal_emoji.get(signal, "ℹ️")
        
        # 기본 정보
        message_parts = [
            f"{emoji} *비트코인 매매 현황 및 통찰*",
            "",
            f"*신호:* {signal}",
            f"*신뢰도:* {confidence:.1%}",
            f"*현재 가격:* ${current_price:,.2f}",
            ""
        ]
        
        # 각종 지표 정보
        message_parts.append("*📊 각종 지표:*")
        if indicators.get("transfer_entropy") is not None:
            te = indicators.get("transfer_entropy", 0.0)
            te_status = "높음 ⚠️" if te > 3.0 else "정상 ✅"
            message_parts.append(f"  • 전이 엔트로피: {te:.2f} ({te_status})")
        
        if indicators.get("market_regime"):
            regime = indicators.get("market_regime", "UNKNOWN")
            message_parts.append(f"  • 시장 국면: {regime}")
        
        if indicators.get("compression_ratio") is not None:
            cr = indicators.get("compression_ratio", 1.0)
            message_parts.append(f"  • 압축률: {cr:.1%}")
        
        if indicators.get("sentiment"):
            sentiment = indicators.get("sentiment", "NEUTRAL")
            message_parts.append(f"  • 감성: {sentiment}")
        
        if indicators.get("news_confidence") is not None:
            news_conf = indicators.get("news_confidence", 0.0)
            message_parts.append(f"  • 뉴스 신뢰도: {news_conf:.1%}")
        
        # 🚀 해역증 지수 (아테나 작전 지침 융합)
        if indicators.get("hae_yeok_index") is not None:
            hae_yeok = indicators.get("hae_yeok_index", 0.0)
            hae_yeok_severity = indicators.get("hae_yeok_severity", "low")
            hae_yeok_status = "Critical 🔴" if hae_yeok_severity == "critical" else \
                             "High ⚠️" if hae_yeok_severity == "high" else \
                             "Medium ⚠️" if hae_yeok_severity == "medium" else "정상 ✅"
            message_parts.append(f"  • 해역증 지수: {hae_yeok:.3f} ({hae_yeok_status})")
        
        if indicators.get("s_m_gap") is not None:
            s_m_gap = indicators.get("s_m_gap", 0.0)
            if s_m_gap > 0.07:  # S-M 괴리 임계값
                message_parts.append(f"  • S-M 괴리: {s_m_gap:.3f} (위험 ⚠️)")
        
        # 🚀 점진적 청산 전략 정보 (아테나 작전 지침 융합)
        if indicators.get("liquidation_ratio") is not None:
            liq_ratio = indicators.get("liquidation_ratio", 0.0)
            liq_reason = indicators.get("liquidation_reason", "")
            if liq_ratio > 0.0:
                message_parts.append(f"  • 청산 비율: {liq_ratio:.1%} ({liq_reason})")
        
        # 예언 묵시록 통찰
        if apocalypse_insight:
            message_parts.append("")
            message_parts.append("*🔮 예언 묵시록 통찰:*")
            
            collapse_risk = apocalypse_insight.get("collapse_risk")
            stability = apocalypse_insight.get("stability")
            apocalypse_signal = apocalypse_insight.get("apocalypse_signal")
            
            if collapse_risk is not None:
                risk_status = "높음 ⚠️" if collapse_risk > 0.7 else "정상 ✅"
                message_parts.append(f"  • 붕괴 위험도: {collapse_risk:.1%} ({risk_status})")
            
            if stability is not None:
                stability_status = "높음 ✅" if stability > 0.8 else "보통 ⚠️"
                message_parts.append(f"  • 안정성: {stability:.1%} ({stability_status})")
            
            if apocalypse_signal:
                message_parts.append(f"  • 묵시록 신호 조정: {apocalypse_signal}")
        
        # 통찰 요약
        message_parts.append("")
        message_parts.append("*💡 통찰 요약:*")
        
        insights = []
        if indicators.get("transfer_entropy", 0.0) > 3.0:
            insights.append("시장 불안정도 높음 - 신중한 접근 권장")
        if indicators.get("market_regime") in ["CRISIS", "VOLATILE"]:
            insights.append("위기/변동성 국면 - 리스크 관리 강화")
        if indicators.get("compression_ratio", 1.0) > 0.8:
            insights.append("노이즈 적음 - 신호 품질 우수")
        # 🚀 해역증 지수 기반 통찰 (아테나 작전 지침 융합)
        if indicators.get("hae_yeok_index") is not None:
            hae_yeok_severity = indicators.get("hae_yeok_severity", "low")
            if hae_yeok_severity in ["high", "critical"]:
                insights.append(f"해역증 감지 ({hae_yeok_severity}) - 과열 버블 위험, 매도 신호 강화 권장")
        if indicators.get("s_m_gap", 0.0) > 0.07:
            insights.append("S-M 괴리 감지 - 붕괴 위험 증가, 리스크 관리 강화")
        # 🚀 점진적 청산 전략 통찰 (아테나 작전 지침 융합)
        if indicators.get("liquidation_ratio", 0.0) > 0.0:
            liq_ratio = indicators.get("liquidation_ratio", 0.0)
            liq_reason = indicators.get("liquidation_reason", "")
            insights.append(f"점진적 청산 권고: {liq_ratio:.1%} ({liq_reason})")
        if apocalypse_insight and apocalypse_insight.get("collapse_risk", 0.0) > 0.7:
            insights.append("묵시록: 붕괴 위험도 높음 - 매도 신호 강화")
        if apocalypse_insight and apocalypse_insight.get("stability", 0.0) > 0.8:
            insights.append("묵시록: 안정성 높음 - 매수 기회")
        
        if insights:
            for i, insight in enumerate(insights, 1):
                message_parts.append(f"  {i}. {insight}")
        else:
            message_parts.append("  • 현재 시장 상황 정상")
        
        # 14B+4D-Native 제언 (감찰/제언용, 매매 실행 아님) - PGAE: 예언 컨텍스트 포함
        if call_path_14b and LLM_14B_AVAILABLE and get_14b_advisory is not None:
            try:
                import asyncio
                prophecy_ctx = {}
                if PROPHECY_CONTEXT_AVAILABLE and load_prophecy_context is not None:
                    try:
                        prophecy_ctx = load_prophecy_context()
                    except Exception:
                        pass
                prophecy_block = ""
                if prophecy_ctx:
                    dd = prophecy_ctx.get("divine_distance", 0)
                    cl = prophecy_ctx.get("crisis_level", "")
                    ps = prophecy_ctx.get("today_summary", "") or ""
                    pd = prophecy_ctx.get("prophecy_direction", "")
                    ps_short = (ps[:120] + "...") if len(ps) > 120 else ps
                    prophecy_block = (
                        f"[예언 컨텍스트] Divine Distance: {dd:.3f}, 위기수준: {cl}, 방향: {pd}. "
                        f"요약: {ps_short}. "
                    )
                prompt_14b = (
                    f"{prophecy_block}"
                    f"현재 비트코인 매매 신호: {signal}, 신뢰도: {confidence:.2f}. "
                    "한 문장으로 4D 균형(S-L-K-M) 관점 제언해줘."
                )
                loop = asyncio.get_event_loop()
                advisory = await loop.run_in_executor(
                    None,
                    lambda: get_14b_advisory(prompt_14b, call_path_14b, timeout_sec=90),
                )
                if advisory:
                    message_parts.append("")
                    message_parts.append("*14B 제언:*")
                    message_parts.append(f"  {advisory}")
            except Exception as e:
                logger.debug("14B 제언 스킵: %s", e)
        
        message_parts.append("")
        message_parts.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        message = "\n".join(message_parts)
        
        await self._send_and_log("trading_insights", message, {
            "signal": signal,
            "confidence": confidence,
            "current_price": current_price,
            "indicators": indicators,
            "apocalypse_insight": apocalypse_insight
        })

