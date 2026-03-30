#!/usr/bin/env python3
"""
Crypto-Nitro v1.6 실전 모의 매매 시스템 (Paper Trading)

가상 레버리지 기반 실전 모의 매매
- 실제 API 호출 없이 시뮬레이션
- Crypto-Nitro v1.6 엔진 통합
- 거대한 줄기 추세 필터 통합
"""
import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np
import logging
import requests  # Binance 공개 API 사용을 위해 추가

# 경로 설정
workspace_root = Path(__file__).parent.parent.parent.parent
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "scripts"))
sys.path.insert(0, str(project_root))  # projects/bitcoin-trading
sys.path.insert(0, str(Path(__file__).parent.parent))

# 모듈 import (경로 수정)
try:
    from src.api.binance_client import BinanceFuturesClient, USE_CCXT
except ImportError:
    # 대체 경로 시도
    try:
        from projects.bitcoin_trading.src.api.binance_client import BinanceFuturesClient, USE_CCXT
    except ImportError:
        # 직접 경로 시도
        import importlib.util
        binance_path = project_root / "src" / "api" / "binance_client.py"
        if binance_path.exists():
            spec = importlib.util.spec_from_file_location("binance_client", binance_path)
            binance_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(binance_module)
            BinanceFuturesClient = binance_module.BinanceFuturesClient
            USE_CCXT = binance_module.USE_CCXT
        else:
            BinanceFuturesClient = None
            USE_CCXT = False
            logger.warning("⚠️ BinanceFuturesClient를 찾을 수 없습니다.")

from src.strategy.crypto_nitro_live_strategy import CryptoNitroLiveStrategy

# 로그 디렉토리 생성
log_dir = workspace_root / "projects" / "bitcoin-trading" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "paper_trading.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CryptoNitroPaperTrader:
    """
    Crypto-Nitro v1.6 실전 모의 매매 시스템
    
    핵심 기능:
    - 실제 API 호출 없이 시뮬레이션
    - 가상 레버리지 자동 조절
    - 실시간 성능 모니터링
    """
    
    def __init__(
        self,
        symbol: str = "BTCUSDT",
        initial_capital: float = 10000.0,
        leverage: int = 2,
        testnet: bool = True,
        use_great_trunk_filter: bool = True,
        paper_trading: bool = True  # 모의 매매 모드
    ):
        """
        Args:
            symbol: 거래 심볼
            initial_capital: 초기 자본
            leverage: 기본 레버리지 (물리적 레버리지, 항상 2배로 고정)
            testnet: 테스트넷 사용 여부
            use_great_trunk_filter: 거대한 줄기 추세 필터 사용 여부
            paper_trading: 모의 매매 모드 (True면 실제 API 호출 안 함)
        """
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.testnet = testnet
        self.use_great_trunk_filter = use_great_trunk_filter
        self.paper_trading = paper_trading
        
        # Binance API 클라이언트 (실전 매매 모드에서는 필수)
        if not paper_trading:
            logger.info("🔐 Binance API 클라이언트 초기화 중...")
            self.binance = BinanceFuturesClient(testnet=testnet)
        else:
            # 모의 매매 모드에서도 가격 조회를 위해 API 클라이언트 사용
            try:
                self.binance = BinanceFuturesClient(testnet=testnet)
                logger.info("📄 모의 매매 모드: 가격 조회를 위해 API 클라이언트 사용")
            except Exception as e:
                logger.warning(f"⚠️ API 클라이언트 초기화 실패 (모의 매매 모드): {e}")
                self.binance = None
        
        # Crypto-Nitro 전략
        logger.info("🚀 Crypto-Nitro v1.6 전략 초기화 중...")
        self.strategy = CryptoNitroLiveStrategy(
            symbol=symbol,
            initial_capital=initial_capital,
            leverage=leverage,
            use_great_trunk_filter=use_great_trunk_filter
        )
        
        # 포지션 추적 (모의 매매)
        self.positions = {
            "LONG": None,  # {"quantity": float, "entry_price": float, "entry_time": datetime}
            "SHORT": None
        }
        
        # 거래 내역
        self.trades_history = []
        
        # 성능 지표
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # 로그 디렉토리 생성
        log_dir = Path("projects/bitcoin-trading/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
    
    async def fetch_price_data(self, limit: int = 100) -> pd.DataFrame:
        """
        가격 데이터 수집 (실시간)
        
        Args:
            limit: 캔들 개수
        
        Returns:
            가격 데이터 DataFrame
        """
        try:
            # 모의 매매 모드와 실전 모드 모두 실제 API로 가격 데이터 수집
            if self.binance:
                try:
                    if USE_CCXT:
                        # CCXT 사용
                        ohlcv = self.binance.exchange.fetch_ohlcv(
                            self.symbol,
                            timeframe='1d',
                            limit=limit
                        )
                        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('date', inplace=True)
                        df['close'] = df['close'].astype(float)
                        df['volatility'] = df['close'].pct_change().rolling(30).std() * np.sqrt(365)
                        df['volatility'] = df['volatility'].fillna(0.485)
                        df['nvt_ratio'] = 50.0  # 기본값 (실제 NVT 계산은 전략에서 수행)
                        logger.info(f"✅ 가격 데이터 수집 완료: {len(df)}개 캔들")
                        return df
                    else:
                        # python-binance 사용
                        klines = self.binance.client.futures_klines(
                            symbol=self.symbol,
                            interval='1d',
                            limit=limit
                        )
                        df = pd.DataFrame(klines, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignore'
                        ])
                        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                        df.set_index('date', inplace=True)
                        df['close'] = df['close'].astype(float)
                        df['volatility'] = df['close'].pct_change().rolling(30).std() * np.sqrt(365)
                        df['volatility'] = df['volatility'].fillna(0.485)
                        df['nvt_ratio'] = 50.0  # 기본값 (실제 NVT 계산은 전략에서 수행)
                        logger.info(f"✅ 가격 데이터 수집 완료: {len(df)}개 캔들")
                        return df
                except Exception as e:
                    logger.error(f"❌ Binance API 캔들 데이터 수집 실패: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback: 공개 API 사용
                    return await self._fetch_price_data_public_api(limit)
            else:
                # Binance API 클라이언트가 없으면 공개 API 사용
                logger.info("📡 Binance 공개 API로 가격 데이터 수집 시도...")
                return await self._fetch_price_data_public_api(limit)
        except Exception as e:
            logger.error(f"❌ 가격 데이터 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            # 최종 Fallback: 공개 API 사용
            return await self._fetch_price_data_public_api(limit)
    
    async def _fetch_price_data_public_api(self, limit: int = 100) -> pd.DataFrame:
        """
        Binance 공개 API로 가격 데이터 수집 (API 키 불필요)
        
        Args:
            limit: 캔들 개수
        
        Returns:
            가격 데이터 DataFrame
        """
        try:
            import requests
            import time
            
            # Binance 공개 API 엔드포인트 (API 키 불필요)
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': self.symbol.replace('USDT', 'USDT'),  # BTCUSDT
                'interval': '1d',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            
            if not klines:
                logger.warning("⚠️ 공개 API에서 데이터를 가져올 수 없습니다.")
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('date', inplace=True)
            df['close'] = df['close'].astype(float)
            df['volatility'] = df['close'].pct_change().rolling(30).std() * np.sqrt(365)
            df['volatility'] = df['volatility'].fillna(0.485)
            df['nvt_ratio'] = 50.0  # 기본값 (실제 NVT 계산은 전략에서 수행)
            
            logger.info(f"✅ 공개 API로 가격 데이터 수집 완료: {len(df)}개 캔들")
            return df
            
        except Exception as e:
            logger.error(f"❌ 공개 API 가격 데이터 수집 실패: {e}")
            return pd.DataFrame()
    
    async def _get_current_price_public_api(self) -> float:
        """
        Binance 공개 API로 현재 가격 조회 (API 키 불필요)
        
        Returns:
            현재 가격 (float) 또는 0.0 (실패 시)
        """
        try:
            import requests
            
            # Binance 공개 API 엔드포인트 (API 키 불필요)
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': self.symbol}  # BTCUSDT
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'price' in data:
                price = float(data['price'])
                logger.debug(f"✅ 공개 API로 현재 가격 조회 성공: {price:,.2f}")
                return price
            else:
                logger.warning("⚠️ 공개 API 응답에 가격 정보가 없습니다.")
                return 0.0
                
        except Exception as e:
            logger.debug(f"⚠️ 공개 API 가격 조회 실패: {e}")
            return 0.0
    
    def execute_live_trade(
        self,
        signal: str,
        price: float,
        confidence: float,
        leverage_multiplier: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        실전 매매 실행 (실제 Binance API 호출)
        
        Args:
            signal: 매매 신호 ("BUY", "SELL", "HOLD")
            price: 현재 가격
            confidence: 신뢰도
            leverage_multiplier: 가상 레버리지 배율
        
        Returns:
            거래 정보
        """
        try:
            if signal == "HOLD":
                return None
            
            if not self.binance:
                logger.error("❌ Binance API 클라이언트가 없습니다")
                return None
            
            # 잔고 조회
            balance = self.binance.get_balance()
            current_balance = balance.get('total', 0.0)
            
            if current_balance <= 0:
                logger.warning("⚠️ 잔고가 없습니다")
                return None
            
            # 주문 수량 계산 (가상 레버리지 적용)
            # Binance 클라이언트에 유틸 함수가 있으면 사용하고,
            # 없으면 내부 안전 로직으로 계산한다.
            if hasattr(self.binance, "calculate_order_quantity"):
                quantity = self.binance.calculate_order_quantity(
                    symbol=self.symbol,
                    current_price=price,
                    leverage_multiplier=leverage_multiplier,
                    confidence=confidence,
                    total_balance=current_balance,
                    base_leverage=float(self.leverage)
                )
            else:
                effective_leverage = self.leverage * leverage_multiplier
                # 전략 레이어 자본의 최대 30%만 기본으로 사용
                target_notional = current_balance * effective_leverage * confidence * 0.3
                quantity = target_notional / price
                quantity = round(quantity, 6)
            
            if quantity <= 0:
                logger.warning(f"⚠️ 계산된 수량이 0 이하입니다: {quantity}")
                return None
            
            # 현재 포지션 확인
            current_position = None
            if self.positions["LONG"] is not None:
                current_position = "LONG"
            elif self.positions["SHORT"] is not None:
                current_position = "SHORT"
            
            # 롱 포지션 진입
            if signal == "BUY" and current_position is None:
                order = self.binance.open_long_position(
                    symbol=self.symbol,
                    leverage_multiplier=leverage_multiplier,
                    confidence=confidence,
                    current_price=price
                )
                
                if order:
                    self.positions["LONG"] = {
                        "quantity": quantity,
                        "entry_price": price,
                        "entry_time": datetime.now(),
                        "leverage_multiplier": leverage_multiplier,
                        "effective_leverage": self.leverage * leverage_multiplier,
                        "confidence": confidence,
                        "order_id": order.get('orderId') if isinstance(order, dict) else None
                    }
                    
                    trade_info = {
                        "timestamp": datetime.now(),
                        "action": "BUY_LONG",
                        "symbol": self.symbol,
                        "price": price,
                        "quantity": quantity,
                        "leverage": self.leverage,
                        "effective_leverage": self.leverage * leverage_multiplier,
                        "leverage_multiplier": leverage_multiplier,
                        "confidence": confidence,
                        "order": order
                    }
                    self.trades_history.append(trade_info)
                    self.total_trades += 1
                    
                    logger.info(
                        f"🚀 [실전 매매] 롱 포지션 진입: {self.symbol} {quantity:.6f} @ {price:,.2f} "
                        f"(효과적 레버리지: {self.leverage * leverage_multiplier:.2f}배)"
                    )
                    
                    return trade_info
            
            # 롱 포지션 청산
            elif signal == "SELL" and current_position == "LONG":
                order = self.binance.close_position(
                    symbol=self.symbol,
                    position_side="LONG"
                )
                
                if order:
                    long_pos = self.positions["LONG"]
                    # 실제 수익은 Binance API로 확인 필요
                    profit = 0.0  # TODO: 실제 포지션 수익 계산
                    profit_rate = 0.0
                    
                    trade_info = {
                        "timestamp": datetime.now(),
                        "action": "SELL_LONG",
                        "symbol": self.symbol,
                        "price": price,
                        "quantity": long_pos["quantity"],
                        "entry_price": long_pos["entry_price"],
                        "profit": profit,
                        "profit_rate": profit_rate,
                        "confidence": confidence,
                        "order": order
                    }
                    self.trades_history.append(trade_info)
                    
                    logger.info(
                        f"🚀 [실전 매매] 롱 포지션 청산: {self.symbol} @ {price:,.2f}"
                    )
                    
                    self.positions["LONG"] = None
                    return trade_info
            
            # 숏 포지션 진입
            elif signal == "SELL" and current_position is None:
                order = self.binance.open_short_position(
                    symbol=self.symbol,
                    leverage_multiplier=leverage_multiplier,
                    confidence=confidence,
                    current_price=price
                )
                
                if order:
                    self.positions["SHORT"] = {
                        "quantity": quantity,
                        "entry_price": price,
                        "entry_time": datetime.now(),
                        "leverage_multiplier": leverage_multiplier,
                        "effective_leverage": self.leverage * leverage_multiplier,
                        "confidence": confidence,
                        "order_id": order.get('orderId') if isinstance(order, dict) else None
                    }
                    
                    trade_info = {
                        "timestamp": datetime.now(),
                        "action": "SELL_SHORT",
                        "symbol": self.symbol,
                        "price": price,
                        "quantity": quantity,
                        "leverage": self.leverage,
                        "effective_leverage": self.leverage * leverage_multiplier,
                        "leverage_multiplier": leverage_multiplier,
                        "confidence": confidence,
                        "order": order
                    }
                    self.trades_history.append(trade_info)
                    self.total_trades += 1
                    
                    logger.info(
                        f"🚀 [실전 매매] 숏 포지션 진입: {self.symbol} {quantity:.6f} @ {price:,.2f} "
                        f"(효과적 레버리지: {self.leverage * leverage_multiplier:.2f}배)"
                    )
                    
                    return trade_info
            
            # 숏 포지션 청산
            elif signal == "BUY" and current_position == "SHORT":
                order = self.binance.close_position(
                    symbol=self.symbol,
                    position_side="SHORT"
                )
                
                if order:
                    short_pos = self.positions["SHORT"]
                    # 실제 수익은 Binance API로 확인 필요
                    profit = 0.0  # TODO: 실제 포지션 수익 계산
                    profit_rate = 0.0
                    
                    trade_info = {
                        "timestamp": datetime.now(),
                        "action": "BUY_SHORT",
                        "symbol": self.symbol,
                        "price": price,
                        "quantity": short_pos["quantity"],
                        "entry_price": short_pos["entry_price"],
                        "profit": profit,
                        "profit_rate": profit_rate,
                        "confidence": confidence,
                        "order": order
                    }
                    self.trades_history.append(trade_info)
                    
                    logger.info(
                        f"🚀 [실전 매매] 숏 포지션 청산: {self.symbol} @ {price:,.2f}"
                    )
                    
                    self.positions["SHORT"] = None
                    return trade_info
            
            return None
        except Exception as e:
            logger.error(f"❌ 실전 매매 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def execute_paper_trade(
        self,
        signal: str,
        price: float,
        confidence: float,
        leverage_multiplier: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        모의 매매 실행
        
        Args:
            signal: 매매 신호 ("BUY", "SELL", "HOLD")
            price: 현재 가격
            confidence: 신뢰도
            leverage_multiplier: 가상 레버리지 배율
        
        Returns:
            거래 정보
        """
        try:
            if signal == "HOLD":
                return None
            
            # 잔고 조회 (모의)
            current_balance = self.initial_capital + self.total_pnl
            
            # 주문 수량 계산 (가상 레버리지 적용)
            # 실제 Binance 클라이언트의 유틸리티 함수가 있으면 사용하고,
            # 없으면 항상 모의 계산 로직을 사용한다.
            if self.binance and hasattr(self.binance, "calculate_order_quantity"):
                quantity = self.binance.calculate_order_quantity(
                    symbol=self.symbol,
                    current_price=price,
                    leverage_multiplier=leverage_multiplier,
                    confidence=confidence,
                    total_balance=current_balance,
                    base_leverage=float(self.leverage)
                )
            else:
                # 모의 매매 모드: 내부 로직으로 안전하게 수량 계산
                effective_leverage = self.leverage * leverage_multiplier
                # 전략 레이어 자본의 최대 30%만 기본으로 사용
                target_notional = current_balance * effective_leverage * confidence * 0.3
                quantity = target_notional / price
                quantity = round(quantity, 6)  # 기본 정밀도
            
            if quantity <= 0:
                logger.warning(f"⚠️ 계산된 수량이 0 이하입니다: {quantity}")
                return None
            
            # 롱 포지션 진입
            if signal == "BUY" and self.positions["LONG"] is None and self.positions["SHORT"] is None:
                self.positions["LONG"] = {
                    "quantity": quantity,
                    "entry_price": price,
                    "entry_time": datetime.now(),
                    "leverage_multiplier": leverage_multiplier,
                    "effective_leverage": self.leverage * leverage_multiplier,
                    "confidence": confidence
                }
                
                trade_info = {
                    "timestamp": datetime.now(),
                    "action": "BUY_LONG",
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": quantity,
                    "leverage": self.leverage,
                    "effective_leverage": self.leverage * leverage_multiplier,
                    "leverage_multiplier": leverage_multiplier,
                    "confidence": confidence
                }
                self.trades_history.append(trade_info)
                self.total_trades += 1
                
                logger.info(
                    f"📄 [모의 매매] 롱 포지션 진입: {self.symbol} {quantity:.6f} @ {price:,.2f} "
                    f"(효과적 레버리지: {self.leverage * leverage_multiplier:.2f}배)"
                )
                
                return trade_info
            
            # 롱 포지션 청산
            elif signal == "SELL" and self.positions["LONG"] is not None:
                long_pos = self.positions["LONG"]
                profit = (price - long_pos["entry_price"]) * long_pos["quantity"]
                profit_rate = (profit / (long_pos["entry_price"] * long_pos["quantity"])) * 100
                
                self.total_pnl += profit
                if profit > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                trade_info = {
                    "timestamp": datetime.now(),
                    "action": "SELL_LONG",
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": long_pos["quantity"],
                    "entry_price": long_pos["entry_price"],
                    "profit": profit,
                    "profit_rate": profit_rate,
                    "confidence": confidence
                }
                self.trades_history.append(trade_info)
                
                logger.info(
                    f"📄 [모의 매매] 롱 포지션 청산: {self.symbol} @ {price:,.2f} "
                    f"(수익: ${profit:,.2f}, 수익률: {profit_rate:.2f}%)"
                )
                
                self.positions["LONG"] = None
                return trade_info
            
            # 숏 포지션 진입
            elif signal == "SELL" and self.positions["LONG"] is None and self.positions["SHORT"] is None:
                self.positions["SHORT"] = {
                    "quantity": quantity,
                    "entry_price": price,
                    "entry_time": datetime.now(),
                    "leverage_multiplier": leverage_multiplier,
                    "effective_leverage": self.leverage * leverage_multiplier,
                    "confidence": confidence
                }
                
                trade_info = {
                    "timestamp": datetime.now(),
                    "action": "SELL_SHORT",
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": quantity,
                    "leverage": self.leverage,
                    "effective_leverage": self.leverage * leverage_multiplier,
                    "leverage_multiplier": leverage_multiplier,
                    "confidence": confidence
                }
                self.trades_history.append(trade_info)
                self.total_trades += 1
                
                logger.info(
                    f"📄 [모의 매매] 숏 포지션 진입: {self.symbol} {quantity:.6f} @ {price:,.2f} "
                    f"(효과적 레버리지: {self.leverage * leverage_multiplier:.2f}배)"
                )
                
                return trade_info
            
            # 숏 포지션 청산
            elif signal == "BUY" and self.positions["SHORT"] is not None:
                short_pos = self.positions["SHORT"]
                profit = (short_pos["entry_price"] - price) * short_pos["quantity"]
                profit_rate = (profit / (short_pos["entry_price"] * short_pos["quantity"])) * 100
                
                self.total_pnl += profit
                if profit > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                trade_info = {
                    "timestamp": datetime.now(),
                    "action": "BUY_SHORT",
                    "symbol": self.symbol,
                    "price": price,
                    "quantity": short_pos["quantity"],
                    "entry_price": short_pos["entry_price"],
                    "profit": profit,
                    "profit_rate": profit_rate,
                    "confidence": confidence
                }
                self.trades_history.append(trade_info)
                
                logger.info(
                    f"📄 [모의 매매] 숏 포지션 청산: {self.symbol} @ {price:,.2f} "
                    f"(수익: ${profit:,.2f}, 수익률: {profit_rate:.2f}%)"
                )
                
                self.positions["SHORT"] = None
                return trade_info
            
            return None
        except Exception as e:
            logger.error(f"❌ 모의 매매 실행 실패: {e}")
            return None
    
    async def run_paper_trading(self, interval_seconds: int = 60):
        """
        모의 매매 루프 실행
        
        Args:
            interval_seconds: 신호 확인 간격 (초)
        """
        mode_name = "모니터링" if self.paper_trading else "실전 매매"
        logger.info(f"🚀 Crypto-Nitro v1.7.1 {mode_name} 시작")
        logger.info(f"   심볼: {self.symbol}")
        logger.info(f"   초기 자본: ${self.initial_capital:,.2f}")
        logger.info(f"   물리적 레버리지: {self.leverage}배")
        logger.info(f"   거대한 줄기 필터: {'활성화' if self.use_great_trunk_filter else '비활성화'}")
        logger.info(f"   확인 간격: {interval_seconds}초")
        if self.paper_trading:
            logger.info(f"   모드: 모니터링 모드 (거래 실행 안 함, 신호만 확인)")
        
        while True:
            try:
                # 현재 가격 조회
                if self.paper_trading:
                    # 모의 매매 모드: 실제 가격 조회
                    current_price = 0.0
                    
                    # 1순위: Binance API 클라이언트 사용 (API 키 있으면)
                    if self.binance:
                        current_price = self.binance.get_current_price(self.symbol)
                    
                    # 2순위: 공개 API 사용 (API 키 없어도 가능)
                    if current_price == 0.0:
                        current_price = await self._get_current_price_public_api()
                    
                    if current_price == 0.0:
                        logger.warning("⚠️ 가격 조회 실패, 다음 주기로 대기")
                        await asyncio.sleep(interval_seconds)
                        continue
                else:
                    # 실전 모드: Binance API로 가격 조회
                    if self.binance:
                        current_price = self.binance.get_current_price(self.symbol)
                        if current_price == 0.0:
                            logger.warning("⚠️ 가격 조회 실패, 다음 주기로 대기")
                            await asyncio.sleep(interval_seconds)
                            continue
                    else:
                        logger.error("❌ Binance API 클라이언트가 없습니다")
                        break
                
                # 가격 데이터 업데이트 (전략에 전달)
                if current_price > 0:
                    # 최신 가격 데이터를 전략에 전달
                    if len(self.strategy.price_data) == 0:
                        # 초기 데이터 로드
                        logger.info("📊 초기 가격 데이터 로드 중...")
                        price_df = await self.fetch_price_data(limit=100)
                        if not price_df.empty:
                            self.strategy.price_data = price_df
                            logger.info(f"✅ 초기 가격 데이터 로드 완료: {len(price_df)}개 캔들")
                        else:
                            logger.warning("⚠️ 가격 데이터를 로드할 수 없습니다. 다음 주기로 대기")
                            await asyncio.sleep(interval_seconds)
                            continue
                    else:
                        # 최신 가격으로 업데이트 (간단한 방식: 마지막 행의 close 값만 업데이트)
                        try:
                            if len(self.strategy.price_data) > 0 and 'close' in self.strategy.price_data.columns:
                                # 현재 가격을 최신 행의 close 값으로 업데이트
                                self.strategy.price_data.iloc[-1, self.strategy.price_data.columns.get_loc('close')] = float(current_price)
                        except Exception as e:
                            logger.debug(f"가격 데이터 업데이트 실패 (무시): {e}")
                            # 실패해도 계속 진행
                
                # 현재 포지션 확인
                current_position = None
                if self.positions["LONG"] is not None:
                    current_position = "LONG"
                elif self.positions["SHORT"] is not None:
                    current_position = "SHORT"
                
                # 매매 신호 생성
                signal_data = self.strategy.calculate_trading_signal(
                    current_price=current_price,
                    current_time=datetime.now()
                )
                
                # 신호 정보 로그 출력 (매 주기마다)
                signal = signal_data.get('signal', 'UNKNOWN')
                confidence = signal_data.get('confidence', 0.0)
                min_confidence = getattr(self.strategy, 'min_confidence', 0.52)
                
                logger.info(
                    f"📊 신호 생성: {signal} | "
                    f"신뢰도: {confidence:.4f} | "
                    f"임계값: {min_confidence:.4f} | "
                    f"레버리지 배율: {signal_data.get('leverage_multiplier', 0.0):.4f} | "
                    f"Lambda: {signal_data.get('lambda_value', 0.0):.4f} | "
                    f"DCV: {signal_data.get('dcv', 0.0):.4f}"
                )
                if signal_data.get("and_gate_reason"):
                    logger.info("🚧 AND 게이트: %s (사유: %s)", signal, signal_data["and_gate_reason"])
                
                # 신뢰도 임계값 체크 로그
                if signal != "HOLD" and confidence < min_confidence:
                    logger.warning(
                        f"⚠️ 신뢰도 부족으로 거래 스킵: {confidence:.4f} < {min_confidence:.4f} "
                        f"(신호: {signal})"
                    )
                
                # 거래 실행 여부 판단
                should_execute, execute_signal, is_switch = self.strategy.should_execute_trade(signal_data, current_position)
                
                # 거래 실행 여부 로그
                if not should_execute and signal != 'HOLD':
                    logger.info(
                        f"⏸️ 거래 실행 스킵: 신호={signal}, "
                        f"신뢰도={confidence:.4f}, "
                        f"현재 포지션={current_position}"
                    )
                
                if should_execute:
                    # 주문 수량 사전 확인 (최소 수량 체크)
                    if self.binance:
                        balance = self.binance.get_balance()
                        current_balance = balance.get('total', 0.0)
                        
                        # 수량 계산
                        quantity = self.binance.calculate_order_quantity(
                            symbol=self.symbol,
                            current_price=current_price,
                            leverage_multiplier=signal_data["leverage_multiplier"],
                            confidence=signal_data["confidence"],
                            total_balance=current_balance,
                            base_leverage=float(self.leverage)
                        )
                        
                        if quantity <= 0:
                            logger.debug(
                                f"⚠️ 계산된 수량이 0 이하입니다: {quantity}. "
                                f"잔액: ${current_balance:,.2f}, 신호: {signal_data['signal']}, "
                                f"레버리지 배율: {signal_data['leverage_multiplier']:.2f}, "
                                f"신뢰도: {signal_data['confidence']:.2f}. 거래 스킵."
                            )
                            await asyncio.sleep(interval_seconds)
                            continue
                    
                    # 거래 실행
                    if not self.paper_trading and self.binance:
                        # 실전 매매: 실제 API 호출
                        trade_result = self.execute_live_trade(
                            signal=signal_data["signal"],
                            price=current_price,
                            confidence=signal_data["confidence"],
                            leverage_multiplier=signal_data["leverage_multiplier"]
                        )
                    else:
                        # 모의 매매: 시뮬레이션
                        trade_result = self.execute_paper_trade(
                            signal=signal_data["signal"],
                            price=current_price,
                            confidence=signal_data["confidence"],
                            leverage_multiplier=signal_data["leverage_multiplier"]
                        )
                    
                    if trade_result:
                        logger.info(
                            f"✅ 거래 실행: {trade_result.get('action', 'UNKNOWN')} | "
                            f"가격: {trade_result.get('price', 0.0):,.2f} | "
                            f"수량: {trade_result.get('quantity', 0.0):.6f} | "
                            f"신뢰도: {trade_result.get('confidence', 0.0):.4f}"
                        )
                    else:
                        logger.warning(f"⚠️ 거래 실행 실패: 신호={signal}, 신뢰도={confidence:.4f}")
                
                # 성능 모니터링 (주기적으로 출력)
                if len(self.trades_history) > 0 and len(self.trades_history) % 10 == 0:
                    self.print_performance_summary()
                    # 주기적으로 로그 저장 (10회 거래마다)
                    self.save_trading_log()
                
                # 대기
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("⏹️ 사용자 중단")
                break
            except Exception as e:
                logger.error(f"❌ 모의 매매 루프 오류: {e}")
                await asyncio.sleep(interval_seconds)
        
        # 최종 성능 요약
        self.print_performance_summary()
        self.save_trading_log()
    
    def print_performance_summary(self):
        """성능 요약 출력"""
        current_balance = self.initial_capital + self.total_pnl
        total_return = (self.total_pnl / self.initial_capital) * 100
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        
        logger.info("=" * 80)
        logger.info("📊 성능 요약")
        logger.info("=" * 80)
        logger.info(f"초기 자본: ${self.initial_capital:,.2f}")
        logger.info(f"현재 자본: ${current_balance:,.2f}")
        logger.info(f"총 수익: ${self.total_pnl:,.2f}")
        logger.info(f"총 수익률: {total_return:.2f}%")
        logger.info(f"총 거래: {self.total_trades}회")
        logger.info(f"승리 거래: {self.winning_trades}회")
        logger.info(f"손실 거래: {self.losing_trades}회")
        logger.info(f"승률: {win_rate:.2f}%")
        logger.info("=" * 80)
    
    def save_trading_log(self):
        """거래 내역 저장"""
        try:
            # 절대 경로 사용
            workspace_root = Path(__file__).parent.parent.parent.parent
            log_dir = workspace_root / "projects" / "bitcoin-trading" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"paper_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            log_data = {
                "symbol": self.symbol,
                "initial_capital": self.initial_capital,
                "final_capital": self.initial_capital + self.total_pnl,
                "total_pnl": self.total_pnl,
                "total_return": (self.total_pnl / self.initial_capital) * 100,
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0,
                "trades_history": [
                    {
                        "timestamp": trade["timestamp"].isoformat() if isinstance(trade.get("timestamp"), datetime) else str(trade.get("timestamp")),
                        **{k: v for k, v in trade.items() if k != "timestamp"}
                    }
                    for trade in self.trades_history
                ]
            }
            
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ 거래 내역 저장 완료: {log_file}")
        except Exception as e:
            logger.error(f"❌ 거래 내역 저장 실패: {e}")


async def main():
    """메인 함수"""
    print("=" * 80)
    print("🏛️ Crypto-Nitro v1.6 실전 모의 매매 시스템")
    print("=" * 80)
    
    # 모의 매매 시스템 초기화
    trader = CryptoNitroPaperTrader(
        symbol="BTCUSDT",
        initial_capital=10000.0,
        leverage=2,
        testnet=True,
        use_great_trunk_filter=True,
        paper_trading=True  # 모의 매매 모드
    )
    
    # 모의 매매 시작
    await trader.run_paper_trading(interval_seconds=60)


if __name__ == "__main__":
    asyncio.run(main())

