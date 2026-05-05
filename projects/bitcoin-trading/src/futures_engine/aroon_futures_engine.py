"""
BTC USDT-M 선물 — 아론(Aroon) 교차 전용 엔진.

- 레거시 ``RealtimeTradingWithMonitoring`` 와 로직·시그널을 섞지 않는다.
- 주문은 기존 ``BinanceFuturesClient`` (헤지 롱/숏)만 사용.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.api.binance_client import BinanceFuturesClient, USE_CCXT
from src.futures_engine.indicators.aroon import aroon_up_down
from src.futures_engine.klines import highs_lows_from_klines

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class _CrossState:
    prev_up: Optional[float] = None
    prev_down: Optional[float] = None


class AroonFuturesEngine:
    """데몬이 기대하는 속성: ``binance``, ``running``, ``alert_manager``, ``run()``, ``get_status()``."""

    def __init__(
        self,
        symbol: str = "BTCUSDT",
        testnet: bool = True,
        initial_capital: float = 1000.0,
        leverage: int = 2,
        enable_trading: bool = False,
    ) -> None:
        self.symbol = str(symbol).strip().upper()
        self.api_symbol = self._resolve_api_symbol(self.symbol)
        self.testnet = bool(testnet)
        self.initial_capital = float(initial_capital)
        self.leverage = int(leverage)
        self.enable_trading = bool(enable_trading)

        self.running = False
        self.alert_manager = None

        self.period = max(2, int(os.getenv("AROON_PERIOD", "25")))
        self.kline_interval = (os.getenv("AROON_KLINE_INTERVAL", "15m").strip() or "15m")
        self.poll_sec = float(os.getenv("AROON_POLL_SEC", "60"))
        self.order_qty = float(os.getenv("AROON_ORDER_QTY", "0.002"))
        self.min_cross_gap = float(os.getenv("AROON_MIN_CROSS_GAP", "2.0"))

        self.binance = BinanceFuturesClient(testnet=self.testnet)
        self._cross = _CrossState()
        self._last_up: Optional[float] = None
        self._last_down: Optional[float] = None
        self._last_signal = "INIT"
        self._loop_i = 0
        self._orders_ok = 0
        self._orders_fail = 0
        self._klimit = max(self.period + 5, 60)

        self.stop_file = PROJECT_ROOT / "memory" / "STOP.txt"
        self._state_file = PROJECT_ROOT / "logs" / "trading_state.json"

    @staticmethod
    def _resolve_api_symbol(symbol: str) -> str:
        """CCXT 선물 심볼 포맷(BTC/USDT:USDT) 보정."""
        s = str(symbol).strip().upper()
        if not USE_CCXT:
            return s
        if "/" in s:
            return s
        if s.endswith("USDT") and len(s) > 4:
            base = s[:-4]
            return f"{base}/USDT:USDT"
        return s

    def _kill_switch(self) -> bool:
        try:
            return self.stop_file.exists()
        except OSError:
            return False

    def _persist_trader_state(self) -> None:
        """Best-effort 호환: 레거시와 동일 파일명으로 최소 필드만 기록."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "schema": "trading_state_aroon_v1",
                "symbol": self.symbol,
                "engine": "aroon_v1",
                "trades_count": self._orders_ok,
                "circuit_breaker_state": {"failure_count": self._orders_fail},
                "last_signal": self._last_signal,
                "aroon_up": self._last_up,
                "aroon_down": self._last_down,
            }
            self._state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.debug("trading_state write skipped: %s", e)

    def _desired_side_from_cross(self, up: float, down: float) -> Optional[str]:
        """
        교차 + 최소 갭으로 방향 확정.
        - 불리시(롱 우세): 이전 up<=down 이고 현재 up>down 이고 (up-down)>=gap
        - 베어리시(숏 우세): 이전 up>=down 이고 현재 up<down 이고 (down-up)>=gap
        """
        gap_req = max(0.0, self.min_cross_gap)
        pu, pd = self._cross.prev_up, self._cross.prev_down
        if pu is None or pd is None:
            return None
        if pu <= pd and up > down and (up - down) >= gap_req:
            return "LONG"
        if pu >= pd and up < down and (down - up) >= gap_req:
            return "SHORT"
        return None

    async def _apply_target_side(self, target: Optional[str]) -> None:
        if not self.enable_trading:
            return
        if target is None:
            return

        pos = self.binance.get_position(self.api_symbol)
        side = None
        qty = 0.0
        if isinstance(pos, dict):
            side = str(pos.get("side") or "").upper()
            try:
                qty = float(pos.get("quantity") or 0)
            except (TypeError, ValueError):
                qty = 0.0

        has_long = side == "LONG" and qty > 0
        has_short = side == "SHORT" and qty > 0

        if target == "LONG":
            if has_short:
                r = self.binance.close_position(self.api_symbol, "SHORT")
                if r is None:
                    self._orders_fail += 1
                    logger.warning("아론: SHORT 청산 실패")
                    return
            if not has_long:
                r2 = self.binance.open_long_position(
                    self.api_symbol, quantity=self.order_qty, leverage=self.leverage
                )
                if r2 is not None:
                    self._orders_ok += 1
                    logger.info("아론: LONG 진입 주문 제출")
                else:
                    self._orders_fail += 1
        elif target == "SHORT":
            if has_long:
                r = self.binance.close_position(self.api_symbol, "LONG")
                if r is None:
                    self._orders_fail += 1
                    logger.warning("아론: LONG 청산 실패")
                    return
            if not has_short:
                r2 = self.binance.open_short_position(
                    self.api_symbol, quantity=self.order_qty, leverage=self.leverage
                )
                if r2 is not None:
                    self._orders_ok += 1
                    logger.info("아론: SHORT 진입 주문 제출")
                else:
                    self._orders_fail += 1

    async def run(self) -> None:
        self.running = True
        logger.info(
            "Aroon 엔진 시작 symbol=%s testnet=%s trading=%s period=%s interval=%s",
            self.symbol,
            self.testnet,
            self.enable_trading,
            self.period,
            self.kline_interval,
        )

        while self.running:
            try:
                if self._kill_switch():
                    logger.warning("STOP 파일 감지 — 아론 엔진 루프 종료")
                    break

                self._loop_i += 1
                raw = self.binance.get_klines(self.api_symbol, self.kline_interval, limit=self._klimit)
                highs, lows = highs_lows_from_klines(raw)
                if USE_CCXT and raw and not highs:
                    # CCXT 심볼 형식일 수 있음 — 클라이언트는 BTCUSDT 유지
                    logger.warning("아론: 캔들 파싱 결과 비어 있음 (CCXT 형식 확인)")

                if len(highs) < self.period:
                    logger.warning(
                        "아론: 캔들 부족 (%s<%s) — 대기",
                        len(highs),
                        self.period,
                    )
                    await asyncio.sleep(self.poll_sec)
                    continue

                up, down = aroon_up_down(highs, lows, self.period)
                self._last_up, self._last_down = up, down

                target = self._desired_side_from_cross(up, down)
                if target:
                    self._last_signal = f"CROSS_{target}"
                    await self._apply_target_side(target)
                else:
                    self._last_signal = "HOLD"

                logger.info(
                    "아론 루프 #%s up=%.2f down=%.2f signal=%s ccxt=%s",
                    self._loop_i,
                    up,
                    down,
                    self._last_signal,
                    USE_CCXT,
                )

                self._cross.prev_up = up
                self._cross.prev_down = down
                self._persist_trader_state()

                await asyncio.sleep(max(5.0, self.poll_sec))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("아론 엔진 루프 오류: %s", e)
                await asyncio.sleep(max(5.0, self.poll_sec))

        self.running = False
        logger.info("Aroon 엔진 종료")

    def get_status(self) -> Dict[str, Any]:
        pos = None
        try:
            pos = self.binance.get_position(self.api_symbol)
        except Exception as e:
            pos = {"error": str(e)}

        hist_size = 0
        try:
            raw = self.binance.get_klines(self.api_symbol, self.kline_interval, limit=self._klimit)
            h, l = highs_lows_from_klines(raw)
            hist_size = min(len(h), len(l))
        except Exception:
            pass

        return {
            "running": self.running,
            "engine": "aroon_v1",
            "trading_enabled": self.enable_trading,
            "symbol": self.symbol,
            "api_symbol": self.api_symbol,
            "testnet": self.testnet,
            "price_history_size": hist_size,
            "aroon": {
                "period": self.period,
                "interval": self.kline_interval,
                "up": self._last_up,
                "down": self._last_down,
                "last_signal": self._last_signal,
            },
            "orders_executed": self._orders_ok,
            "orders_failed": self._orders_fail,
            "loop_iteration": self._loop_i,
            "position_snapshot": pos,
            "mkm_singular_core": {
                "total_signals": self._loop_i,
                "buy_count": self._orders_ok if "LONG" in self._last_signal else 0,
                "sell_count": self._orders_ok if "SHORT" in self._last_signal else 0,
                "locked_count": 0,
                "locked_ratio": None,
                "buy_ratio": None,
                "sell_ratio": None,
                "last_signal_summary": self._last_signal,
            },
        }
