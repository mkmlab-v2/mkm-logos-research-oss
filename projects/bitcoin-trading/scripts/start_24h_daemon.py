#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 24시간 자동매매 데몬 시작 스크립트

안티그래비티 기반 24시간 무중단 자동매매 시스템 실행

작성일: 2026-02-06
"""

import sys
import os
import asyncio
import json
import atexit
import io
from pathlib import Path
from typing import Any

# ⚠️ 외부 벡터 DB 사용 금지: 비트코인 트레이딩 프로젝트에서는 외부 벡터 DB를 사용하지 않음
os.environ["DISABLE_QDRANT"] = "true"

PROJECT_ROOT = Path(__file__).parent.parent
LOCK_PATH = PROJECT_ROOT / "memory" / "daemon_singleton.lock"
LOCK_HANDLE: io.TextIOWrapper | None = None
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.daemon.bitcoin_trading_daemon import BitcoinTradingDaemon
from src.config.config_loader import load_config
from src.futures_engine import futures_engine_mode


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_dotenv_map(path: Path) -> dict[str, str]:
    env_map: dict[str, str] = {}
    if not path.is_file():
        return env_map
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            env_map[key] = value
    return env_map


def _monorepo_dotenv_path() -> Path:
    """Prefer project root .env, then workspace root .env, then parent fallback."""
    project_candidate = PROJECT_ROOT / ".env"
    if project_candidate.is_file():
        return project_candidate
    workspace = Path(__file__).resolve().parent.parent.parent.parent
    workspace_candidate = workspace / ".env"
    if workspace_candidate.is_file():
        return workspace_candidate
    return PROJECT_ROOT.parent / ".env"


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_singleton_lock() -> bool:
    """
    Ensure single runtime for start_24h_daemon.py.
    Returns True when lock is acquired, False when another active owner exists.
    """
    global LOCK_HANDLE
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Strong singleton lock on Windows (OS-level file lock).
    # This prevents duplicate runtimes even when PID metadata is stale/missing.
    try:
        if os.name == "nt":
            import msvcrt

            lock_file = open(LOCK_PATH, "a+", encoding="utf-8")
            try:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                lock_file.close()
                print("⚠️ 이미 실행 중인 데몬 감지 (OS lock). 중복 기동을 차단합니다.")
                return False
            LOCK_HANDLE = lock_file
    except Exception as e:
        print(f"⚠️ 강한 락 초기화 실패(보조 PID 점검으로 진행): {e}")

    if LOCK_PATH.exists():
        try:
            payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            old_pid = int(payload.get("pid", 0))
            if old_pid > 0 and _pid_is_running(old_pid):
                print(f"⚠️ 이미 실행 중인 데몬 감지 (PID={old_pid}). 중복 기동을 차단합니다.")
                return False
        except Exception:
            pass

    payload = {"pid": os.getpid(), "entrypoint": "scripts/start_24h_daemon.py"}
    payload_text = json.dumps(payload, ensure_ascii=False)
    try:
        if LOCK_HANDLE is not None:
            LOCK_HANDLE.seek(0)
            LOCK_HANDLE.truncate()
            LOCK_HANDLE.write(payload_text)
            LOCK_HANDLE.flush()
        else:
            LOCK_PATH.write_text(payload_text, encoding="utf-8")
    except PermissionError:
        print("⚠️ 락 메타데이터 기록 실패. 중복 기동 위험으로 실행을 중단합니다.")
        return False
    return True


def _release_singleton_lock():
    global LOCK_HANDLE
    try:
        if LOCK_HANDLE is not None and os.name == "nt":
            try:
                import msvcrt

                LOCK_HANDLE.seek(0)
                msvcrt.locking(LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            try:
                LOCK_HANDLE.close()
            except Exception:
                pass
            LOCK_HANDLE = None

        if LOCK_PATH.exists():
            payload = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            if int(payload.get("pid", -1)) == os.getpid():
                LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass


async def main():
    """24시간 자동매매 데몬 시작"""
    # SSOT 우선: trading_config.yaml -> 환경 변수 override
    config_path = PROJECT_ROOT / "config" / "trading_config.yaml"
    config = load_config(config_path) if callable(load_config) else {}
    config = config if isinstance(config, dict) else {}
    risk_cfg = config.get("risk_management", {}) if isinstance(config.get("risk_management"), dict) else {}

    cfg_symbol = config.get("symbol", "BTCUSDT")
    cfg_testnet = _parse_bool(config.get("testnet"), True)
    cfg_initial_capital = float(config.get("initial_capital", risk_cfg.get("initial_capital", 1000.0)))
    cfg_leverage = int(config.get("leverage", 2))
    cfg_enable_trading = _parse_bool(
        config.get("enable_live_trading", config.get("enable_trading")),
        False,
    )

    dotenv = _read_dotenv_map(_monorepo_dotenv_path())

    # 프로젝트 `.env` → PM2에 없을 때만 os.environ에 반영 (Binance + 런타임 플래그).
    for env_key in (
        "MKM_SINGULAR_CORE_THRESHOLD",
        "MKM_SINGULAR_CORE_GRID",
        "MKM_MIN_CONFIDENCE",
        "BTC_FUTURES_ENGINE",
        "AROON_PERIOD",
        "AROON_KLINE_INTERVAL",
        "AROON_POLL_SEC",
        "AROON_ORDER_QTY",
        "AROON_MIN_CROSS_GAP",
        "MKM_MAKER_ONLY",
        "MKM_STRICT_MAKER_ENFORCEMENT",
        "MKM_FEE_GUARD_MAX_TRADES_PER_DAY",
        "POSITION_MIN_HOLD_SECONDS",
        "REVERSAL_COOLDOWN_SECONDS",
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "BINANCE_KEY_SOURCE_MODE",
        "TESTNET",
        "ENABLE_TRADING",
        "SYMBOL",
        "INITIAL_CAPITAL",
        "LEVERAGE",
    ):
        if env_key in dotenv and str(dotenv.get(env_key, "")).strip():
            if not os.environ.get(env_key, "").strip():
                os.environ[env_key] = str(dotenv[env_key]).strip()

    symbol = os.getenv("SYMBOL", str(cfg_symbol))
    testnet_raw = os.getenv("TESTNET")
    if testnet_raw is None:
        testnet_raw = dotenv.get("TESTNET")
    testnet = _parse_bool(testnet_raw, cfg_testnet)
    initial_capital = float(os.getenv("INITIAL_CAPITAL", str(cfg_initial_capital)))
    leverage = int(os.getenv("LEVERAGE", str(cfg_leverage)))
    enable_raw = os.getenv("ENABLE_TRADING")
    if enable_raw is None:
        enable_raw = dotenv.get("ENABLE_TRADING")
    enable_trading = _parse_bool(enable_raw, cfg_enable_trading)
    
    print("="*80)
    print("🚀 24시간 비트코인 자동매매 데몬")
    print("="*80)
    print()
    print("📋 설정:")
    print(f"   - 심볼: {symbol}")
    print(f"   - 테스트넷: {testnet} ({'안전 모드' if testnet else '실전 모드'})")
    print(f"   - 초기 자본: {initial_capital:.2f} USDT")
    print(f"   - 레버리지: {leverage}배")
    print(f"   - 거래: {'활성화' if enable_trading else '비활성화 (모니터링만)'}")
    print(f"   - 선물 엔진: {futures_engine_mode()} (BTC_FUTURES_ENGINE; legacy=통합엔진 / aroon_v1=아론)")
    print("   - 자동 재시작: 활성화")
    print()
    if not testnet and enable_trading:
        print("⚠️ 경고: 실전 거래 모드가 활성화되었습니다!")
    print("⚠️ 주의:")
    print("   - 이 데몬은 24시간 무중단 실행됩니다")
    print("   - 중단하려면 Ctrl+C를 누르세요")
    print()
    print("="*80)
    print()
    
    daemon = BitcoinTradingDaemon(
        symbol=symbol,
        testnet=testnet,
        initial_capital=initial_capital,
        leverage=leverage,
        enable_trading=enable_trading,
        max_restart_attempts=10,
        restart_delay=60  # 60초 후 재시작
    )
    
    await daemon.run()


if __name__ == "__main__":
    try:
        if not _acquire_singleton_lock():
            sys.exit(0)
        atexit.register(_release_singleton_lock)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
        sys.exit(0)

