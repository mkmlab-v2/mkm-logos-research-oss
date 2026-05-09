#!/usr/bin/env python3
"""
Binance Futures API 클라이언트 (Security Agent 통합)

Security Agent에서 암호화된 API 키를 가져와서 사용
"""
import sys
import os
import time
import uuid
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging

# Security Agent 통합 (모노레포 루트 = workspace; scripts/는 루트에 있음)
try:
    workspace_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(workspace_root))
    from scripts.security_agent_manager import get_security_agent
    SECURITY_AGENT_AVAILABLE = True
except ImportError:
    SECURITY_AGENT_AVAILABLE = False
    # Security Agent가 없어도 환경 변수/파일 폴백이 정상 경로이므로 import 시점 경고는 낮춘다.
    logging.info("Security Agent unavailable at import time; using env/file fallback.")

# Binance API (python-binance 또는 ccxt)
BINANCE_AVAILABLE = False
USE_CCXT = False

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
    USE_CCXT = False
except ImportError:
    try:
        import ccxt
        BINANCE_AVAILABLE = True
        USE_CCXT = True
    except ImportError:
        BINANCE_AVAILABLE = False
        USE_CCXT = False
        logging.warning("⚠️ Binance API 라이브러리를 설치하세요: pip install python-binance 또는 pip install ccxt")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _is_invalid_credential_value(value: Optional[str]) -> bool:
    """
    Detect obviously broken credential strings.

    This guards against accidental shell error text being written
    into `.env` (e.g., keepass command not found output).
    """
    if value is None:
        return True

    v = value.strip()
    if not v:
        return True

    invalid_markers = (
        "commandnotfoundexception",
        "the term 'keepassxc-cli' is not recognized",
        "fullyqualifiederrorid",
        "categoryinfo",
        "at line:",
        "keepassxc-cli :",
    )
    lowered = v.lower()
    if any(marker in lowered for marker in invalid_markers):
        return True

    # Binance keys are compact tokens; multi-line/powershell trace-like values are invalid.
    if "\n" in v or "\r" in v or len(v) < 16:
        return True

    return False


def _read_key_from_dotenv(dotenv_path: Path, key: str) -> Optional[str]:
    """Read a single KEY=value from .env safely (no shell expansion)."""
    try:
        if not dotenv_path.exists():
            return None
        prefix = f"{key}="
        for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or not line.startswith(prefix):
                continue
            value = line[len(prefix):].strip()
            if " #" in value:
                value = value.split(" #", 1)[0].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value.strip() or None
    except Exception:
        return None
    return None


def _credential_source_mode() -> str:
    """
    Credential source routing mode.
    - auto (default): security_agent -> env -> dotenv -> file
    - dotenv_only: only workspace/current .env
    - env_only: only process env
    """
    raw = os.getenv("BINANCE_KEY_SOURCE_MODE", "auto")
    return str(raw or "auto").strip().lower()


def get_binance_api_keys() -> tuple[str, str]:
    """
    Binance API 키 가져오기 (우선순위: Security Agent > 환경 변수 > 파일)
    
    파일 위치: projects/bitcoin-trading/binance_api_keys.json
    파일 형식:
    {
        "api_key": "your_api_key",
        "api_secret": "your_api_secret",
        "testnet": true  // 선택적
    }
    
    Returns:
        (api_key, api_secret) 튜플
    """
    api_key = None
    api_secret = None
    source_mode = _credential_source_mode()
    dotenv_only = source_mode in ("dotenv_only", "dotenv")
    env_only = source_mode in ("env_only", "env")
    
    # 1. Security Agent에서 가져오기 (최우선)
    if SECURITY_AGENT_AVAILABLE and not (dotenv_only or env_only):
        try:
            agent = get_security_agent()
            api_key = agent.get_env_var("BINANCE_API_KEY")
            api_secret = agent.get_env_var("BINANCE_API_SECRET")
            if api_key and api_secret:
                api_key, api_secret = api_key.strip(), api_secret.strip()
                if not (_is_invalid_credential_value(api_key) or _is_invalid_credential_value(api_secret)):
                    logger.info("✅ Security Agent에서 Binance API 키를 가져왔습니다.")
                    logger.info("   사용 중인 API 키 (끝 4자): ...%s (Binance 화면의 키와 동일한지 확인)", api_key[-4:] if len(api_key) >= 4 else "****")
                    _publish_binance_credential_meta(credential_source="security_agent", api_key=api_key)
                    return api_key, api_secret
                logger.warning("⚠️ Security Agent에서 가져온 Binance API 키 형식이 비정상입니다. 다음 소스로 폴백합니다.")
        except Exception as e:
            logger.warning(f"⚠️ Security Agent에서 API 키 가져오기 실패: {e}")
    
    # 2. 환경 변수에서 가져오기 (원래 작동하던 방식 우선)
    if not dotenv_only:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if api_key is not None:
            api_key = api_key.strip()
        if api_secret is not None:
            api_secret = api_secret.strip()
        
        if api_key and api_secret:
            if not (_is_invalid_credential_value(api_key) or _is_invalid_credential_value(api_secret)):
                logger.info("✅ 환경 변수에서 Binance API 키를 가져왔습니다.")
                logger.info("   사용 중인 API 키 (끝 4자): ...%s (Binance 화면의 키와 동일한지 확인)", api_key[-4:] if len(api_key) >= 4 else "****")
                _publish_binance_credential_meta(credential_source="env", api_key=api_key)
                return api_key, api_secret
            logger.warning("⚠️ 환경 변수 BINANCE_API_KEY/BINANCE_API_SECRET 값이 비정상입니다. 파일 소스로 폴백합니다.")
    
    # 3. .env 파일에서 가져오기 (데몬/스케줄러 환경 드리프트 방지)
    if not env_only:
        try:
            dotenv_candidates = [
                Path(__file__).resolve().parents[4] / ".env",  # C:/workspace/.env
                Path.cwd() / ".env",
            ]
            for dotenv in dotenv_candidates:
                k = _read_key_from_dotenv(dotenv, "BINANCE_API_KEY")
                s = _read_key_from_dotenv(dotenv, "BINANCE_API_SECRET")
                if k and s and not (_is_invalid_credential_value(k) or _is_invalid_credential_value(s)):
                    logger.info("✅ .env 파일에서 Binance API 키를 가져왔습니다.")
                    logger.info("   .env 경로: %s", dotenv)
                    logger.info("   사용 중인 API 키 (끝 4자): ...%s (Binance 화면의 키와 동일한지 확인)", k[-4:] if len(k) >= 4 else "****")
                    _publish_binance_credential_meta(credential_source=f"dotenv:{dotenv}", api_key=k)
                    return k, s
        except Exception as e:
            logger.warning("⚠️ .env에서 API 키 가져오기 실패: %s", e)

    # 4. 파일에서 가져오기 (보조 PC용 - 환경 변수/.env가 없을 때만)
    if not (dotenv_only or env_only):
        try:
            # 프로젝트 루트 디렉토리 찾기 (여러 경로 시도)
            current_file = Path(__file__)
            possible_roots = [
                current_file.parent.parent.parent,  # src/api/binance_client.py -> projects/bitcoin-trading
                current_file.parent.parent.parent.parent,  # workspace/projects/bitcoin-trading
                Path.cwd(),  # 현재 작업 디렉토리
                Path(__file__).parent.parent.parent if '__file__' in globals() else Path.cwd(),  # 스크립트 실행 위치
            ]

            api_keys_file = None
            for root in possible_roots:
                test_file = root / "binance_api_keys.json"
                if test_file.exists():
                    api_keys_file = test_file
                    logger.info(f"📁 API 키 파일 발견: {api_keys_file}")
                    break

            # 현재 스크립트 위치 기준으로도 시도
            if not api_keys_file:
                script_dir = Path.cwd()
                test_file = script_dir / "binance_api_keys.json"
                if test_file.exists():
                    api_keys_file = test_file
                    logger.info(f"📁 API 키 파일 발견 (현재 디렉토리): {api_keys_file}")

            if api_keys_file and api_keys_file.exists():
                import json
                with open(api_keys_file, 'r', encoding='utf-8') as f:
                    keys_data = json.load(f)
                    api_key = keys_data.get("api_key")
                    api_secret = keys_data.get("api_secret")

                    if api_key and api_secret:
                        api_key, api_secret = api_key.strip(), api_secret.strip()
                        if not (_is_invalid_credential_value(api_key) or _is_invalid_credential_value(api_secret)):
                            logger.info("✅ 파일에서 Binance API 키를 가져왔습니다.")
                            logger.info("   파일 위치: %s", api_keys_file)
                            logger.info("   사용 중인 API 키 (끝 4자): ...%s (Binance 화면의 키와 동일한지 확인)", api_key[-4:] if len(api_key) >= 4 else "****")
                            _publish_binance_credential_meta(credential_source=f"file:{api_keys_file}", api_key=api_key)
                            return api_key, api_secret
                        logger.warning(f"⚠️ API 키 파일 값 형식이 비정상입니다: {api_keys_file}")
                    else:
                        logger.warning(f"⚠️ 파일에 API 키 또는 Secret이 없습니다: {api_keys_file}")
            else:
                logger.debug(f"🔍 API 키 파일을 찾지 못했습니다. 시도한 경로: {[str(r / 'binance_api_keys.json') for r in possible_roots]}")
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON 형식 오류: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 파일에서 API 키 가져오기 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    # 5. 키가 없으면 None 반환
    logger.error("❌ Binance API 키를 찾을 수 없습니다. (source_mode=%s)", source_mode)
    logger.error("   다음 중 하나를 설정하세요:")
    logger.error("   1. Security Agent에 저장")
    logger.error("   2. 환경 변수 설정 (BINANCE_API_KEY, BINANCE_API_SECRET)")
    logger.error("   3. binance_api_keys.json 파일 생성 (프로젝트 루트)")
    return None, None


def compute_offset_stop_prices(
    *,
    entry: float,
    position_side: str,
    sl_pct: Optional[float],
    tp_pct: Optional[float],
) -> tuple[Optional[float], Optional[float]]:
    """Derive raw SL/TP trigger prices from %-of-entry offsets (LONG/SHORT)."""
    ps = str(position_side).upper()
    sl_px: Optional[float] = None
    tp_px: Optional[float] = None
    if sl_pct is not None and sl_pct > 0:
        if ps == "LONG":
            sl_px = float(entry) * (1.0 - float(sl_pct) / 100.0)
        elif ps == "SHORT":
            sl_px = float(entry) * (1.0 + float(sl_pct) / 100.0)
    if tp_pct is not None and tp_pct > 0:
        if ps == "LONG":
            tp_px = float(entry) * (1.0 + float(tp_pct) / 100.0)
        elif ps == "SHORT":
            tp_px = float(entry) * (1.0 - float(tp_pct) / 100.0)
    return sl_px, tp_px


def validate_protective_triggers(
    *,
    position_side: str,
    mark: float,
    sl_px: Optional[float],
    tp_px: Optional[float],
) -> Optional[str]:
    """Return error message if triggers are inconsistent with mark (exchange will reject)."""
    ps = str(position_side).upper()
    eps = max(float(mark) * 1e-9, 1e-8)
    if ps == "LONG":
        if sl_px is not None and float(sl_px) >= float(mark) - eps:
            return f"LONG stop-loss stopPrice ({sl_px}) must be below mark ({mark})"
        if tp_px is not None and float(tp_px) <= float(mark) + eps:
            return f"LONG take-profit stopPrice ({tp_px}) must be above mark ({mark})"
    elif ps == "SHORT":
        if sl_px is not None and float(sl_px) <= float(mark) + eps:
            return f"SHORT stop-loss stopPrice ({sl_px}) must be above mark ({mark})"
        if tp_px is not None and float(tp_px) >= float(mark) - eps:
            return f"SHORT take-profit stopPrice ({tp_px}) must be below mark ({mark})"
    return None


class BinanceFuturesClient:
    """
    Binance Futures API 클라이언트 (2배 레버리지, 롱/숏 지원)
    
    Security Agent 통합: 암호화된 API 키 자동 로드
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,  # 테스트넷 사용 권장
        maker_only: bool = False,
        api_use_ed25519: bool = False,
    ):
        """
        Args:
            api_key: Binance API 키 (None이면 Security Agent에서 자동 로드)
            api_secret: Binance API 시크릿 (None이면 Security Agent에서 자동 로드)
            testnet: 테스트넷 사용 여부 (True 권장)
            maker_only: True면 LIMIT + timeInForce=GTX(Post-Only)로 Maker 수수료만 적용 (FDUSD 0%)
            api_use_ed25519: True면 Ed25519 서명 사용 (4대 정책 권장). 현재 미구현 시 HMAC 사용.
        """
        # 4대 정책(2026-03-12): Ed25519 요청 시 미구현 안내 (현재 HMAC 사용)
        if api_use_ed25519:
            logger.warning("⚠️ API Ed25519 서명은 아직 미구현입니다. HMAC 서명을 사용합니다.")
        # API 키가 없으면 configured source chain에서 가져오기
        keys_loaded_from_source = False
        if not api_key or not api_secret:
            api_key, api_secret = get_binance_api_keys()
            if not api_key or not api_secret:
                raise ValueError("Binance API 키를 찾을 수 없습니다. Security Agent 또는 환경 변수를 설정하세요.")
            keys_loaded_from_source = True
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.maker_only = maker_only
        self._last_time_sync_at = 0.0
        
        # Rate Limit 관리 (Binance Futures API 제한)
        # - Weight Limit: 1200 / 1분
        # - Order Limit: 300 / 10초
        self.rate_limiter = {
            "weight_limit": 1200,  # 1분당 가중치 제한
            "order_limit": 300,  # 10초당 주문 제한
            "current_weight": 0,
            "current_orders": 0,
            "weight_reset_time": time.time(),
            "order_reset_time": time.time(),
            "last_reset": time.time()
        }
        
        if not BINANCE_AVAILABLE:
            raise ImportError("Binance API 라이브러리를 설치하세요: pip install python-binance 또는 pip install ccxt")
        
        if USE_CCXT:
            # CCXT 사용
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # 선물 거래
                    'test': testnet  # 테스트넷
                }
            })
            self.client = None
        else:
            # python-binance 사용
            if testnet:
                # 테스트넷: https://testnet.binancefuture.com/
                self.client = Client(api_key, api_secret, testnet=True)
            else:
                # 실전: https://www.binance.com/
                self.client = Client(api_key, api_secret)
            self.exchange = None
            
            # Hedge Mode 활성화 (롱/숏 동시 보유 가능)
            try:
                self._sync_server_time_offset(force=True)
                self.set_position_mode(dual_side_position=True)
            except Exception as e:
                logger.warning(f"⚠️ 포지션 모드 설정 실패 (이미 설정되었을 수 있음): {e}")

        if not keys_loaded_from_source:
            _publish_binance_credential_meta(credential_source="explicit_arg", api_key=self.api_key)

    def _sync_server_time_offset(self, force: bool = False) -> None:
        """
        Sync local timestamp offset for signed futures endpoints.
        Fixes Binance -1021 errors (timestamp ahead/behind server time).
        """
        if USE_CCXT or not getattr(self, "client", None):
            return
        now = time.time()
        if not force and (now - self._last_time_sync_at) < 30:
            return
        try:
            server = self.client.futures_time()
            server_ms = int(server.get("serverTime", 0))
            local_ms = int(time.time() * 1000)
            self.client.timestamp_offset = server_ms - local_ms
            self._last_time_sync_at = now
            logger.info("⏱️ Binance server time synced (offset_ms=%s)", self.client.timestamp_offset)
        except Exception as e:
            logger.warning("⚠️ 서버 시간 동기화 실패: %s", e)

    def _call_client(self, fn):
        """
        Execute signed API call with one-time server-time resync retry on -1021.
        """
        try:
            return fn()
        except Exception as e:
            if not USE_CCXT and getattr(e, "code", None) == -1021:
                logger.warning("⚠️ Binance timestamp skew detected (-1021), resync + retry.")
                self._sync_server_time_offset(force=True)
                return fn()
            raise
    
    @staticmethod
    def _normalize_futures_symbol(symbol: Union[str, None]) -> Optional[str]:
        """USDT-M 선물 심볼 (예: BTCUSDT). 빈 값·슬래시 형식 방지."""
        if symbol is None:
            return None
        s = str(symbol).strip().upper()
        if "/" in s:
            s = s.replace("/", "").replace("-", "")
        return s if len(s) >= 5 else None

    @staticmethod
    def _coerce_leverage_int(leverage: Union[int, float, str, None]) -> int:
        """
        Binance changeLeverage는 정수 배수만 허용. YAML 2.0·문자열 float가 -1102를 유발할 수 있음.
        """
        lev = int(round(float(leverage)))
        return max(1, min(lev, 125))

    def set_leverage(self, symbol: str, leverage: Union[int, float] = 2) -> bool:
        """
        레버리지 설정 (2배)
        
        Args:
            symbol: 거래 심볼 (예: "BTCUSDT")
            leverage: 레버리지 배수 (기본값: 2)
        """
        try:
            if USE_CCXT:
                # CCXT는 레버리지 설정이 자동으로 처리됨
                return True
            sym = self._normalize_futures_symbol(symbol)
            if not sym:
                logger.error("❌ 레버리지 설정 실패: 유효하지 않은 심볼 %r", symbol)
                return False
            lev = self._coerce_leverage_int(leverage)
            # python-binance - 공식 API (leverage는 정수 필수)
            self._call_client(lambda: self.client.futures_change_leverage(symbol=sym, leverage=lev))
            logger.info(f"✅ 레버리지 설정 완료: {sym} {lev}배")
            return True
        except Exception as e:
            code = getattr(e, "code", None)
            if code == -1102:
                logger.error(
                    "❌ 레버리지 설정 실패 (-1102 BAD_PARAMETER): symbol=%r leverage=%r → 정수·심볼 확인",
                    symbol,
                    leverage,
                )
            else:
                logger.error("❌ 레버리지 설정 실패: %s", e)
            return False
    
    def set_position_mode(self, dual_side_position: bool = True) -> bool:
        """
        포지션 모드 설정 (Hedge Mode 활성화)
        
        Args:
            dual_side_position: True = Hedge Mode (롱/숏 동시 보유 가능), False = One-way Mode
        """
        try:
            if not USE_CCXT:
                # python-binance
                self._call_client(lambda: self.client.futures_change_position_mode(dualSidePosition=dual_side_position))
                mode = "Hedge Mode" if dual_side_position else "One-way Mode"
                logger.info(f"✅ 포지션 모드 설정 완료: {mode}")
                return True
            return True
        except Exception as e:
            code = getattr(e, "code", None)
            # -4059: 이미 목표 모드로 설정됨
            if code == -4059:
                logger.info(f"✅ 포지션 모드 이미 설정됨 (변경 불필요): {e}")
                return True
            # -4067: 미체결 주문/포지션 존재 시 모드 변경 불가
            # 운영 중에는 흔한 상태 충돌이므로 치명 실패 대신 경고로 처리한다.
            if code == -4067:
                logger.warning(
                    "⚠️ 포지션 모드 변경 보류(-4067): 오픈 오더/포지션 정리 후 재시도 필요 (%s)",
                    e,
                )
                return True
            logger.error(f"❌ 포지션 모드 설정 실패: {e}")
            return False
    
    def _check_rate_limit(self, weight: int = 1, is_order: bool = False):
        """
        Rate Limit 확인 및 대기
        
        Args:
            weight: API 호출 가중치 (기본값: 1)
            is_order: 주문 API 호출 여부 (기본값: False)
        """
        current_time = time.time()
        limiter = self.rate_limiter
        
        # Weight Limit 체크 (1분당 1200)
        if current_time - limiter["weight_reset_time"] >= 60:
            limiter["weight_reset_time"] = current_time
            limiter["current_weight"] = 0
        
        if limiter["current_weight"] + weight > limiter["weight_limit"]:
            wait_time = 60 - (current_time - limiter["weight_reset_time"])
            if wait_time > 0:
                logger.warning(f"⚠️ Weight Limit 도달, {wait_time:.1f}초 대기...")
                time.sleep(wait_time)
                limiter["weight_reset_time"] = time.time()
                limiter["current_weight"] = 0
        
        limiter["current_weight"] += weight
        
        # Order Limit 체크 (10초당 300)
        if is_order:
            if current_time - limiter["order_reset_time"] >= 10:
                limiter["order_reset_time"] = current_time
                limiter["current_orders"] = 0
            
            if limiter["current_orders"] >= limiter["order_limit"]:
                wait_time = 10 - (current_time - limiter["order_reset_time"])
                if wait_time > 0:
                    logger.warning(f"⚠️ Order Limit 도달, {wait_time:.1f}초 대기...")
                    time.sleep(wait_time)
                    limiter["order_reset_time"] = time.time()
                    limiter["current_orders"] = 0
            
            limiter["current_orders"] += 1
    
    def get_current_price(self, symbol: str = "BTCUSDT") -> float:
        """현재 가격 조회"""
        try:
            # Rate Limit 체크 (가격 조회는 weight 1)
            self._check_rate_limit(weight=1)
            
            if USE_CCXT:
                ticker = self.exchange.fetch_ticker(symbol)
                return float(ticker['last'])
            else:
                ticker = self._call_client(lambda: self.client.futures_symbol_ticker(symbol=symbol))
                return float(ticker['price'])
        except Exception as e:
            logger.error(f"❌ 가격 조회 실패: {e}")
            return 0.0

    def _get_order_book(self, symbol: str, limit: int = 5) -> tuple[float, float]:
        """호가창에서 best bid, best ask 조회. (best_bid, best_ask)."""
        try:
            self._check_rate_limit(weight=1)
            if USE_CCXT:
                ob = self.exchange.fetch_order_book(symbol, limit)
                best_bid = float(ob["bids"][0][0]) if ob["bids"] else 0.0
                best_ask = float(ob["asks"][0][0]) if ob["asks"] else 0.0
                return best_bid, best_ask
            book = self._call_client(lambda: self.client.futures_order_book(symbol=symbol, limit=limit))
            best_bid = float(book["bids"][0][0]) if book.get("bids") else 0.0
            best_ask = float(book["asks"][0][0]) if book.get("asks") else 0.0
            return best_bid, best_ask
        except Exception as e:
            logger.warning(f"⚠️ 호가창 조회 실패, 현재가 사용: {e}")
            p = self.get_current_price(symbol)
            return p, p

    def _get_tick_size(self, symbol: str) -> float:
        """심볼 가격 틱 크기 (exchangeInfo PRICE_FILTER)."""
        try:
            self._check_rate_limit(weight=1)
            if not USE_CCXT and self.client:
                info = self._call_client(lambda: self.client.futures_exchange_info())
                for s in info.get("symbols", []):
                    if s["symbol"] == symbol:
                        for f in s.get("filters", []):
                            if f.get("filterType") == "PRICE_FILTER":
                                return float(f["tickSize"])
            return 0.1  # BTC 기본
        except Exception:
            return 0.1

    def _get_lot_size_filter(self, symbol: str) -> tuple[float, float, float]:
        """USD-M LOT_SIZE: (min_qty, max_qty, step_size). Used to avoid API -1111 precision errors."""
        defaults = (0.001, 9000.0, 0.001)
        try:
            self._check_rate_limit(weight=1)
            if not USE_CCXT and self.client:
                info = self._call_client(lambda: self.client.futures_exchange_info())
                for s in info.get("symbols", []):
                    if s.get("symbol") != symbol:
                        continue
                    for f in s.get("filters", []):
                        if f.get("filterType") == "LOT_SIZE":
                            return (float(f["minQty"]), float(f["maxQty"]), float(f["stepSize"]))
                    return defaults
            if USE_CCXT and self.exchange:
                self.exchange.load_markets()
                m = self.exchange.market(symbol)
                lo = (m.get("limits") or {}).get("amount") or {}
                min_q = float(lo.get("min") or defaults[0])
                max_q = float(lo.get("max") or defaults[1])
                prec_amt = (m.get("precision") or {}).get("amount")
                if isinstance(prec_amt, int) and prec_amt >= 0:
                    step = float(10 ** (-prec_amt))
                else:
                    step = defaults[2]
                return (min_q, max_q, step)
        except Exception as e:
            logger.warning("LOT_SIZE lookup failed for %s: %s — using defaults", symbol, e)
        return defaults

    @staticmethod
    def _floor_quantity_to_lot(quantity: float, min_qty: float, max_qty: float, step: float) -> float:
        """Floor quantity to LOT_SIZE step (never round up — avoids exceeding intended max size)."""
        from decimal import Decimal, ROUND_DOWN

        if quantity is None or quantity <= 0 or step <= 0:
            return 0.0
        q = (Decimal(str(quantity)) / Decimal(str(step))).quantize(Decimal("1"), rounding=ROUND_DOWN) * Decimal(str(step))
        out = float(q)
        if out < min_qty:
            return 0.0
        if out > max_qty:
            cap = (Decimal(str(max_qty)) / Decimal(str(step))).quantize(Decimal("1"), rounding=ROUND_DOWN) * Decimal(str(step))
            out = float(cap)
        return out

    def _quantize_open_quantity(self, symbol: str, quantity: float) -> Optional[float]:
        min_q, max_q, step = self._get_lot_size_filter(symbol)
        adj = self._floor_quantity_to_lot(quantity, min_q, max_q, step)
        if adj <= 0:
            logger.error(
                "❌ 수량 LOT_SIZE 불가: 원본=%s step=%s min=%s (step 배수로 내림 시 최소 미만 — 수량을 올리세요)",
                quantity,
                step,
                min_q,
            )
            return None
        if abs(adj - quantity) > 1e-12:
            logger.info("수량 LOT_SIZE 내림: %s -> %s (step=%s, min=%s)", quantity, adj, step, min_q)
        return adj

    @staticmethod
    def _round_to_tick(price: float, tick_size: float, down: bool = False) -> float:
        """가격을 틱 크기로 반올림. down=True면 내림(롱 매수용)."""
        if tick_size <= 0:
            return price
        from decimal import Decimal, ROUND_DOWN, ROUND_UP
        d = Decimal(str(price))
        tick = Decimal(str(tick_size))
        if down:
            q = (d / tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick
        else:
            q = (d / tick).quantize(Decimal("1"), rounding=ROUND_UP) * tick
        return float(q)

    @staticmethod
    def _build_client_order_id(intent: str) -> str:
        """
        Build Binance-safe idempotency key for order placement.
        Max length is limited (Binance: 36 chars).
        """
        ts = int(time.time() * 1000) % 10_000_000
        nonce = uuid.uuid4().hex[:10]
        tag = "".join(ch for ch in str(intent).lower() if ch.isalnum())[:8] or "order"
        return f"mkm{tag}{ts}{nonce}"[:36]

    @staticmethod
    def _workspace_root_path() -> Path:
        # projects/bitcoin-trading/src/api/binance_client.py -> C:/workspace
        return Path(__file__).resolve().parents[4]

    def _execution_gate_allow(
        self,
        *,
        symbol: str,
        intent_type: str,
        side: str,
        quantity: float,
        position_side: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        Enforce centralized execution gate before any live order placement.
        Returns (allow, reason).
        """
        workspace = self._workspace_root_path()
        gate_script = workspace / "scripts" / "run_execution_gate_v1.py"
        if not gate_script.exists():
            return False, f"execution_gate_script_missing:{gate_script.as_posix()}"

        out_dir = workspace / "reports" / "binance_usdm_single_order"
        out_dir.mkdir(parents=True, exist_ok=True)
        intent_path = out_dir / "runtime_execution_intent_latest.json"
        decision_path = out_dir / "runtime_execution_gate_decision_latest.json"
        payload: Dict[str, Any] = {
            "schema": "execution_intent_v1",
            "request_id": f"{intent_type}-{symbol}-{int(time.time())}",
            "symbol": symbol,
            "side": side,
            "qty": float(quantity),
            "intent_type": intent_type,
            "position_side": position_side,
            "testnet": self.testnet,
        }
        if extra:
            payload["extra"] = extra
        intent_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        proc = subprocess.run(
            [sys.executable, str(gate_script), "--intent-path", str(intent_path), "--output-path", str(decision_path)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True, "allow"
        reason = (proc.stderr or proc.stdout or f"execution_gate_blocked_exit:{proc.returncode}").strip()
        return False, reason or "execution_gate_blocked"

    def open_long_position(
        self,
        symbol: str = "BTCUSDT",
        quantity: float = None,
        leverage: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        롱 포지션 진입 (상방 수익).
        maker_only=True면 LIMIT BUY + timeInForce=GTX(Post-Only)로 Maker만 사용.
        """
        try:
            self._check_rate_limit(weight=1, is_order=True)
            self.set_leverage(symbol, leverage)

            q_adj = self._quantize_open_quantity(symbol, float(quantity))
            if q_adj is None:
                return None
            quantity = q_adj
            allow, reason = self._execution_gate_allow(
                symbol=symbol,
                intent_type="open_long_position",
                side="BUY",
                quantity=quantity,
                position_side="LONG",
                extra={"maker_only": self.maker_only, "leverage": leverage},
            )
            if not allow:
                logger.error("❌ 실행 게이트 차단(open_long_position): %s", reason)
                return None

            if self.maker_only and not USE_CCXT:
                best_bid, _ = self._get_order_book(symbol)
                tick = self._get_tick_size(symbol)
                price = self._round_to_tick(best_bid, tick, down=True)
                if price <= 0:
                    price = self.get_current_price(symbol)
                order = self._call_client(lambda: self.client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='LIMIT',
                    timeInForce='GTX',
                    quantity=quantity,
                    price=price,
                    positionSide='LONG',
                    newClientOrderId=self._build_client_order_id("openlong"),
                ))
                logger.info(f"✅ 롱 포지션 진입 (Maker-only): {symbol} LIMIT {quantity} @ {price} GTX")
                return order
            if self.maker_only and USE_CCXT:
                best_bid, _ = self._get_order_book(symbol)
                order = self.exchange.create_order(
                    symbol=symbol, type='limit', side='buy', amount=quantity, price=best_bid,
                    params={
                        'timeInForce': 'GTX',
                        'positionSide': 'LONG',
                        'newClientOrderId': self._build_client_order_id("openlong"),
                    }
                )
                logger.info(f"✅ 롱 포지션 진입 (Maker-only): {symbol} LIMIT {quantity} @ {best_bid} GTX")
                return order
            if USE_CCXT:
                order = self.exchange.create_market_order(
                    symbol=symbol, side='buy', amount=quantity,
                    params={'leverage': leverage, 'positionSide': 'LONG'}
                )
            else:
                order = self._call_client(lambda: self.client.futures_create_order(
                    symbol=symbol, side='BUY', type='MARKET',
                    quantity=quantity,
                    positionSide='LONG',
                    newClientOrderId=self._build_client_order_id("openlong"),
                ))
            logger.info(f"✅ 롱 포지션 진입: {symbol} {quantity} @ {leverage}배 레버리지")
            return order
        except Exception as e:
            logger.error(f"❌ 롱 포지션 진입 실패: {e}")
            return None
    
    def open_short_position(
        self,
        symbol: str = "BTCUSDT",
        quantity: float = None,
        leverage: int = 2
    ) -> Optional[Dict[str, Any]]:
        """
        숏 포지션 진입 (하방 수익).
        maker_only=True면 LIMIT SELL + timeInForce=GTX(Post-Only)로 Maker만 사용.
        """
        try:
            self._check_rate_limit(weight=1, is_order=True)
            self.set_leverage(symbol, leverage)

            q_adj = self._quantize_open_quantity(symbol, float(quantity))
            if q_adj is None:
                return None
            quantity = q_adj
            allow, reason = self._execution_gate_allow(
                symbol=symbol,
                intent_type="open_short_position",
                side="SELL",
                quantity=quantity,
                position_side="SHORT",
                extra={"maker_only": self.maker_only, "leverage": leverage},
            )
            if not allow:
                logger.error("❌ 실행 게이트 차단(open_short_position): %s", reason)
                return None

            if self.maker_only and not USE_CCXT:
                _, best_ask = self._get_order_book(symbol)
                tick = self._get_tick_size(symbol)
                price = self._round_to_tick(best_ask, tick, down=False)
                if price <= 0:
                    price = self.get_current_price(symbol)
                order = self._call_client(lambda: self.client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    timeInForce='GTX',
                    quantity=quantity,
                    price=price,
                    positionSide='SHORT',
                    newClientOrderId=self._build_client_order_id("openshort"),
                ))
                logger.info(f"✅ 숏 포지션 진입 (Maker-only): {symbol} LIMIT {quantity} @ {price} GTX")
                return order
            if self.maker_only and USE_CCXT:
                _, best_ask = self._get_order_book(symbol)
                order = self.exchange.create_order(
                    symbol=symbol, type='limit', side='sell', amount=quantity, price=best_ask,
                    params={
                        'timeInForce': 'GTX',
                        'positionSide': 'SHORT',
                        'newClientOrderId': self._build_client_order_id("openshort"),
                    }
                )
                logger.info(f"✅ 숏 포지션 진입 (Maker-only): {symbol} LIMIT {quantity} @ {best_ask} GTX")
                return order
            if USE_CCXT:
                order = self.exchange.create_market_order(
                    symbol=symbol, side='sell', amount=quantity,
                    params={'leverage': leverage, 'positionSide': 'SHORT'}
                )
            else:
                order = self._call_client(lambda: self.client.futures_create_order(
                    symbol=symbol, side='SELL', type='MARKET',
                    quantity=quantity,
                    positionSide='SHORT',
                    newClientOrderId=self._build_client_order_id("openshort"),
                ))
            logger.info(f"✅ 숏 포지션 진입: {symbol} {quantity} @ {leverage}배 레버리지")
            return order
        except Exception as e:
            logger.error(f"❌ 숏 포지션 진입 실패: {e}")
            return None
    
    def close_position(
        self,
        symbol: str = "BTCUSDT",
        position_side: str = "LONG"
    ) -> Optional[Dict[str, Any]]:
        """
        포지션 청산.
        maker_only=True면 LIMIT + reduceOnly + GTX 시도 (실패 시 MARKET 청산은 호출부에서 처리 권장).
        """
        try:
            requested_side = str(position_side or "LONG").upper()
            if requested_side not in {"LONG", "SHORT"}:
                logger.error(f"❌ 잘못된 position_side 요청: {position_side}")
                return None
            if USE_CCXT:
                positions = self.exchange.fetch_positions([symbol])
                for pos in positions:
                    if pos['side'] == requested_side.lower() and pos['contracts'] > 0:
                        close_side = 'sell' if requested_side == 'LONG' else 'buy'
                        amt = abs(pos['contracts'])
                        if self.maker_only:
                            best_bid, best_ask = self._get_order_book(symbol)
                            price = best_bid if requested_side == 'LONG' else best_ask
                            order = self.exchange.create_order(
                                symbol=symbol, type='limit', side=close_side, amount=amt, price=price,
                                params={
                                    'timeInForce': 'GTX',
                                    'positionSide': requested_side,
                                    'reduceOnly': True,
                                    'newClientOrderId': self._build_client_order_id("close"),
                                }
                            )
                            logger.info(f"✅ 포지션 청산 (Maker-only): {symbol} {requested_side} LIMIT @ {price} GTX")
                        else:
                            order = self.exchange.create_market_order(
                                symbol=symbol, side=close_side, amount=amt,
                                params={
                                    'positionSide': requested_side,
                                    'newClientOrderId': self._build_client_order_id("close"),
                                }
                            )
                            logger.info(f"✅ 포지션 청산: {symbol} {requested_side}")
                        return order
            else:
                positions = self._call_client(lambda: self.client.futures_position_information(symbol=symbol))
                for pos in positions:
                    if str(pos.get('positionSide') or '').upper() != requested_side:
                        continue
                    position_amt = float(pos['positionAmt'])
                    if position_amt != 0:
                        if position_amt > 0:
                            side = 'SELL'
                            close_position_side = 'LONG'
                        else:
                            side = 'BUY'
                            close_position_side = 'SHORT'
                        qty = abs(position_amt)
                        allow, reason = self._execution_gate_allow(
                            symbol=symbol,
                            intent_type="close_position",
                            side=side,
                            quantity=qty,
                            position_side=close_position_side,
                            extra={"requested_position_side": requested_side, "maker_only": self.maker_only},
                        )
                        if not allow:
                            logger.error("❌ 실행 게이트 차단(close_position): %s", reason)
                            return None
                        if self.maker_only:
                            best_bid, best_ask = self._get_order_book(symbol)
                            tick = self._get_tick_size(symbol)
                            price = self._round_to_tick(best_bid, tick, down=True) if close_position_side == 'LONG' else self._round_to_tick(best_ask, tick, down=False)
                            order = self._call_client(lambda: self.client.futures_create_order(
                                symbol=symbol,
                                side=side,
                                type='LIMIT',
                                timeInForce='GTX',
                                quantity=qty,
                                price=price,
                                positionSide=close_position_side,
                                reduceOnly=True,
                                newClientOrderId=self._build_client_order_id("close"),
                            ))
                            if str(order.get('positionSide') or '').upper() != requested_side:
                                logger.error(
                                    "❌ 청산 주문 side 불일치: requested=%s order.positionSide=%s",
                                    requested_side,
                                    order.get('positionSide'),
                                )
                                return None
                            logger.info(f"✅ 포지션 청산 (Maker-only): {symbol} {close_position_side} LIMIT @ {price} GTX")
                        else:
                            order = self._call_client(lambda: self.client.futures_create_order(
                                symbol=symbol,
                                side=side,
                                type='MARKET',
                                quantity=qty,
                                positionSide=close_position_side,
                                newClientOrderId=self._build_client_order_id("close"),
                            ))
                            if str(order.get('positionSide') or '').upper() != requested_side:
                                logger.error(
                                    "❌ 청산 주문 side 불일치: requested=%s order.positionSide=%s",
                                    requested_side,
                                    order.get('positionSide'),
                                )
                                return None
                            logger.info(f"✅ 포지션 청산: {symbol} {close_position_side}")
                        return order
            logger.warning(f"⚠️ 청산할 포지션이 없습니다: {symbol} {requested_side}")
            return None
        except Exception as e:
            logger.error(f"❌ 포지션 청산 실패: {e}")
            return None
    
    def get_balance(self) -> Dict[str, float]:
        """잔고 조회"""
        try:
            if USE_CCXT:
                balance = self.exchange.fetch_balance()
                return {
                    'USDT': balance.get('USDT', {}).get('free', 0.0),
                    'total': balance.get('USDT', {}).get('total', 0.0)
                }
            else:
                balance = self._call_client(lambda: self.client.futures_account_balance())
                for b in balance:
                    if b['asset'] == 'USDT':
                        return {
                            'USDT': float(b['availableBalance']),
                            'total': float(b['balance'])
                        }
        except Exception as e:
            logger.error(f"❌ 잔고 조회 실패: {e}")
            return {'USDT': 0.0, 'total': 0.0}
    
    def get_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "5m",
        limit: int = 100
    ) -> list:
        """
        캔들스틱 데이터 조회 (가격 데이터 수집용)
        
        Args:
            symbol: 거래 심볼 (예: "BTCUSDT")
            interval: 시간 간격 (예: "1m", "5m", "1h", "1d")
            limit: 조회할 캔들 수 (기본값: 100)
        
        Returns:
            캔들스틱 데이터 리스트
        """
        try:
            if USE_CCXT:
                # CCXT 사용
                ohlcv = self.exchange.fetch_ohlcv(symbol, interval, limit=limit)
                return ohlcv
            else:
                # python-binance 사용
                klines = self._call_client(lambda: self.client.futures_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit
                ))
                return klines
        except Exception as e:
            logger.error(f"❌ 캔들스틱 데이터 조회 실패: {e}")
            return []
    
    def get_position(self, symbol: str = "BTCUSDT") -> Optional[Dict[str, Any]]:
        """
        현재 포지션 정보 조회
        
        Args:
            symbol: 거래 심볼 (예: "BTCUSDT")
        
        Returns:
            포지션 정보 딕셔너리 또는 None
        """
        try:
            if USE_CCXT:
                # CCXT 사용
                positions = self.exchange.fetch_positions([symbol])
                for pos in positions:
                    if pos['contracts'] != 0:
                        return {
                            'symbol': symbol,
                            'side': 'LONG' if pos['side'] == 'long' else 'SHORT',
                            'quantity': abs(pos['contracts']),
                            'entry_price': pos['entryPrice'],
                            'mark_price': pos['markPrice'],
                            'unrealized_pnl': pos['unrealizedPnl']
                        }
                return None
            else:
                # python-binance 사용
                positions = self._call_client(lambda: self.client.futures_position_information(symbol=symbol))
                for pos in positions:
                    position_amt = float(pos['positionAmt'])
                    if position_amt != 0:
                        return {
                            'symbol': symbol,
                            'side': 'LONG' if position_amt > 0 else 'SHORT',
                            'quantity': abs(position_amt),
                            'entry_price': float(pos['entryPrice']),
                            'mark_price': float(pos['markPrice']),
                            'unrealized_pnl': float(pos['unRealizedProfit'])
                        }
                return None
        except Exception as e:
            logger.error(f"❌ 포지션 정보 조회 실패: {e}")
            return None

    def get_open_orders(self, symbol: str = "BTCUSDT") -> list[Dict[str, Any]]:
        """현재 미체결 주문 목록 조회."""
        try:
            if USE_CCXT:
                return self.exchange.fetch_open_orders(symbol=symbol)
            return self._call_client(lambda: self.client.futures_get_open_orders(symbol=symbol))
        except Exception as e:
            logger.error(f"❌ 미체결 주문 조회 실패: {e}")
            return []

    def round_protective_stop_price(
        self,
        symbol: str,
        position_side: str,
        *,
        kind: str,
        price: float,
    ) -> float:
        """
        Round stop/trigger price to PRICE_FILTER tick (conservative vs adverse fill).
        kind: \"sl\" | \"tp\"
        """
        tick = self._get_tick_size(symbol)
        ps = str(position_side).upper()
        kd = str(kind).lower()
        if ps == "LONG":
            return self._round_to_tick(price, tick, down=(kd == "sl"))
        if ps == "SHORT":
            return self._round_to_tick(price, tick, down=(kd == "tp"))
        return self._round_to_tick(price, tick, down=True)

    def place_stop_market_reduce_only(
        self,
        symbol: str,
        position_side: str,
        quantity: float,
        stop_price: float,
        *,
        working_type: str = "MARK_PRICE",
    ) -> Optional[Dict[str, Any]]:
        """
        Hedge mode: STOP_MARKET reduce-only (e.g. LONG stop-loss below market).
        python-binance 전용 (CCXT는 미구현).
        """
        if USE_CCXT:
            logger.error("place_stop_market_reduce_only: CCXT 미구현 — python-binance 사용.")
            return None
        ps = str(position_side).upper()
        close_side = "SELL" if ps == "LONG" else "BUY"
        q_adj = self._quantize_open_quantity(symbol, float(quantity))
        if q_adj is None:
            return None
        allow, reason = self._execution_gate_allow(
            symbol=symbol,
            intent_type="place_stop_market_reduce_only",
            side=close_side,
            quantity=q_adj,
            position_side=ps,
            extra={"working_type": working_type, "stop_price": float(stop_price)},
        )
        if not allow:
            logger.error("❌ 실행 게이트 차단(place_stop_market_reduce_only): %s", reason)
            return None
        sp = self.round_protective_stop_price(symbol, ps, kind="sl", price=float(stop_price))
        try:
            self._check_rate_limit(weight=1, is_order=True)
            order = self._call_client(
                lambda: self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    positionSide=ps,
                    type="STOP_MARKET",
                    stopPrice=sp,
                    quantity=q_adj,
                    workingType=working_type,
                    newClientOrderId=self._build_client_order_id("stopsl"),
                )
            )
            logger.info("✅ STOP_MARKET reduce-only: %s %s stopPrice=%s qty=%s", symbol, ps, sp, q_adj)
            return order
        except Exception as e:
            logger.error("❌ STOP_MARKET 실패: %s", e)
            return None

    def place_take_profit_market_reduce_only(
        self,
        symbol: str,
        position_side: str,
        quantity: float,
        stop_price: float,
        *,
        working_type: str = "MARK_PRICE",
    ) -> Optional[Dict[str, Any]]:
        """
        Hedge mode: TAKE_PROFIT_MARKET reduce-only (e.g. LONG take-profit above market).
        python-binance 전용 (CCXT는 미구현).
        """
        if USE_CCXT:
            logger.error("place_take_profit_market_reduce_only: CCXT 미구현 — python-binance 사용.")
            return None
        ps = str(position_side).upper()
        close_side = "SELL" if ps == "LONG" else "BUY"
        q_adj = self._quantize_open_quantity(symbol, float(quantity))
        if q_adj is None:
            return None
        allow, reason = self._execution_gate_allow(
            symbol=symbol,
            intent_type="place_take_profit_market_reduce_only",
            side=close_side,
            quantity=q_adj,
            position_side=ps,
            extra={"working_type": working_type, "stop_price": float(stop_price)},
        )
        if not allow:
            logger.error("❌ 실행 게이트 차단(place_take_profit_market_reduce_only): %s", reason)
            return None
        sp = self.round_protective_stop_price(symbol, ps, kind="tp", price=float(stop_price))
        try:
            self._check_rate_limit(weight=1, is_order=True)
            order = self._call_client(
                lambda: self.client.futures_create_order(
                    symbol=symbol,
                    side=close_side,
                    positionSide=ps,
                    type="TAKE_PROFIT_MARKET",
                    stopPrice=sp,
                    quantity=q_adj,
                    workingType=working_type,
                    newClientOrderId=self._build_client_order_id("stoptp"),
                )
            )
            logger.info("✅ TAKE_PROFIT_MARKET reduce-only: %s %s stopPrice=%s qty=%s", symbol, ps, sp, q_adj)
            return order
        except Exception as e:
            logger.error("❌ TAKE_PROFIT_MARKET 실패: %s", e)
            return None

    def get_recent_fills(self, symbol: str = "BTCUSDT", limit: int = 50) -> list[Dict[str, Any]]:
        """최근 체결(거래) 내역 조회."""
        try:
            if USE_CCXT:
                trades = self.exchange.fetch_my_trades(symbol=symbol, limit=limit)
                return trades if isinstance(trades, list) else []
            trades = self._call_client(lambda: self.client.futures_account_trades(symbol=symbol, limit=limit))
            return trades if isinstance(trades, list) else []
        except Exception as e:
            logger.error(f"❌ 최근 체결 조회 실패: {e}")
            return []

    @staticmethod
    def _ccxt_linear_futures_symbol(symbol: str) -> str:
        """Map BTCUSDT -> BTC/USDT:USDT for ccxt binance linear futures."""
        u = (symbol or "").upper().replace(" ", "")
        if u.endswith("USDT") and len(u) > 4:
            base = u[:-4]
            return f"{base}/USDT:USDT"
        return symbol

    def fetch_futures_trades_time_range(
        self,
        symbol: str = "BTCUSDT",
        *,
        start_ms: int,
        end_ms: int,
        max_trades: int = 20_000,
    ) -> list[Dict[str, Any]]:
        """
        USDT-M futures account trades in [start_ms, end_ms] (inclusive by time).
        Paginates (1000 / request). Returns raw-native rows (python-binance shape) or
        ccxt rows normalized to the same keys the export script expects.
        """
        if end_ms < start_ms:
            return []
        out: list[Dict[str, Any]] = []
        if USE_CCXT and self.exchange is not None:
            market = self._ccxt_linear_futures_symbol(symbol)
            since = int(start_ms)
            while len(out) < max_trades:
                batch = self.exchange.fetch_my_trades(
                    market,
                    since=since,
                    limit=min(1000, max_trades - len(out)),
                )
                if not batch:
                    break
                for t in batch:
                    if not isinstance(t, dict):
                        continue
                    ts = int(t.get("timestamp") or 0)
                    if ts < start_ms:
                        continue
                    if ts > end_ms:
                        continue
                    out.append(t)
                if len(batch) < 1000:
                    break
                since = int(batch[-1].get("timestamp") or 0) + 1
                if since > end_ms:
                    break
            return out[:max_trades]

        if self.client is None:
            return []

        from_id: Optional[int] = None
        while len(out) < max_trades:
            remaining = max_trades - len(out)
            lim = min(1000, remaining)
            if from_id is None:
                trades = self._call_client(
                    lambda: self.client.futures_account_trades(
                        symbol=symbol,
                        startTime=start_ms,
                        endTime=end_ms,
                        limit=lim,
                    )
                )
            else:
                trades = self._call_client(
                    lambda fid=from_id, lm=lim: self.client.futures_account_trades(
                        symbol=symbol,
                        fromId=fid,
                        limit=lm,
                    )
                )
            if not trades:
                break
            if not isinstance(trades, list):
                break
            for row in trades:
                if not isinstance(row, dict):
                    continue
                try:
                    tt = int(row.get("time") or 0)
                except (TypeError, ValueError):
                    continue
                if tt < start_ms:
                    continue
                if tt > end_ms:
                    continue
                out.append(row)
            if len(trades) < lim:
                break
            try:
                last_id = int(trades[-1].get("id"))
            except (TypeError, ValueError):
                break
            from_id = last_id + 1
            if len(trades) == 1000:
                try:
                    last_t = int(trades[-1].get("time") or 0)
                except (TypeError, ValueError):
                    last_t = 0
                if last_t > end_ms:
                    break
        return out[:max_trades]


def get_last_binance_credential_meta() -> Dict[str, Any]:
    """
    Non-secret metadata for runtime dashboards (exchange_runtime_state).
    Populated when BinanceFuturesClient last constructed successfully; otherwise defaults.
    """
    return dict(_LAST_BINANCE_CREDENTIAL_META)


_LAST_BINANCE_CREDENTIAL_META: Dict[str, Any] = {
    "credential_source": "unknown",
    "credential_key_suffix": "****",
}


def _publish_binance_credential_meta(*, credential_source: str, api_key: Optional[str]) -> None:
    global _LAST_BINANCE_CREDENTIAL_META
    suf = "****"
    if api_key and isinstance(api_key, str) and len(api_key) >= 4:
        suf = api_key[-4:]
    _LAST_BINANCE_CREDENTIAL_META = {
        "credential_source": str(credential_source or "unknown"),
        "credential_key_suffix": suf,
    }


def get_last_binance_credential_meta() -> Dict[str, Any]:
    """
    Non-secret metadata for runtime dashboards (exchange_runtime_state).
    Populated when BinanceFuturesClient last constructed successfully; otherwise defaults.
    """
    return dict(_LAST_BINANCE_CREDENTIAL_META)


_LAST_BINANCE_CREDENTIAL_META: Dict[str, Any] = {
    "credential_source": "unknown",
    "credential_key_suffix": "****",
}


def _publish_binance_credential_meta(*, credential_source: str, api_key: Optional[str]) -> None:
    global _LAST_BINANCE_CREDENTIAL_META
    suf = "****"
    if api_key and isinstance(api_key, str) and len(api_key) >= 4:
        suf = api_key[-4:]
    _LAST_BINANCE_CREDENTIAL_META = {
        "credential_source": str(credential_source or "unknown"),
        "credential_key_suffix": suf,
    }


# Backward compatibility for legacy imports.
BinanceClient = BinanceFuturesClient
