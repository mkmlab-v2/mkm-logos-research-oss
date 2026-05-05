"""BTC USDT-M 선물 전용 엔진 패키지 (레거시 RealtimeTradingWithMonitoring 과 분리).

선택은 환경 변수 ``BTC_FUTURES_ENGINE`` 만으로 통일한다.

- 미설정 / ``legacy`` : 기존 ``RealtimeTradingWithMonitoring`` (기본)
- ``aroon_v1``       : 아론(Aroon) 교차 시그널 + ``BinanceFuturesClient`` 주문 경로

구현 클래스: ``src.futures_engine.aroon_futures_engine.AroonFuturesEngine`` (지연 import 권장)

관련 환경 변수 (선택):

- ``AROON_PERIOD`` (기본 25)
- ``AROON_KLINE_INTERVAL`` (기본 15m)
- ``AROON_POLL_SEC`` (기본 60)
- ``AROON_ORDER_QTY`` (기본 0.002)
- ``AROON_MIN_CROSS_GAP`` (기본 2.0)
"""

from __future__ import annotations

import os

__all__ = ["futures_engine_mode", "is_aroon_engine_requested"]


def futures_engine_mode() -> str:
    raw = (os.environ.get("BTC_FUTURES_ENGINE") or "").strip().lower()
    return raw if raw else "legacy"


def is_aroon_engine_requested() -> bool:
    m = futures_engine_mode()
    return m in {"aroon", "aroon_v1"}
