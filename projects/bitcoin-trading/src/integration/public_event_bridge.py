#!/usr/bin/env python3
"""Sanitized public-event bridge for read-only dashboard feeds."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib import request

logger = logging.getLogger(__name__)

SOURCE_NAME = "unified-trading-monitor"
SCHEMA_VERSION = "public-event.v1"


@dataclass(frozen=True)
class PublicEvent:
    timestamp: str
    active_character_id: str
    risk_level: str
    public_signal_direction: str
    abstract_reason: str
    schema_version: str = SCHEMA_VERSION
    event_id: str = ""
    source: str = SOURCE_NAME
    position_symbol: Optional[str] = None
    position_side: Optional[str] = None
    position_size: Optional[float] = None
    unrealized_pnl_usdt: Optional[float] = None
    realized_24h_usdt: Optional[float] = None
    pnl_24h_type: Optional[str] = None
    balance_total_usdt: Optional[float] = None
    balance_available_usdt: Optional[float] = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "active_character_id": self.active_character_id,
            "risk_level": self.risk_level,
            "public_signal_direction": self.public_signal_direction,
            "abstract_reason": self.abstract_reason,
            "schema_version": self.schema_version,
            "event_id": self.event_id or str(uuid.uuid4()),
            "source": self.source,
            "position_symbol": self.position_symbol,
            "position_side": self.position_side,
            "position_size": self.position_size,
            "unrealized_pnl_usdt": self.unrealized_pnl_usdt,
            "realized_24h_usdt": self.realized_24h_usdt,
            "pnl_24h_type": self.pnl_24h_type,
            "balance_total_usdt": self.balance_total_usdt,
            "balance_available_usdt": self.balance_available_usdt,
        }


class PublicEventBridge:
    def __init__(self, webhook_url: Optional[str] = None, token: Optional[str] = None, queue_size: int = 256):
        self.webhook_url = webhook_url or os.getenv("PUBLIC_EVENT_BRIDGE_WEBHOOK_URL", "").strip()
        self.token = token or os.getenv("PUBLIC_EVENT_BRIDGE_TOKEN", "").strip()
        self._queue: "asyncio.Queue[PublicEvent]" = asyncio.Queue(maxsize=max(8, int(queue_size)))
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        if not self.webhook_url:
            logger.warning("⚠️ PUBLIC_EVENT_BRIDGE_WEBHOOK_URL 미설정 - 브리지 비활성")
            return
        self._running = True
        self._task = asyncio.create_task(self._worker())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def publish_nowait(self, event: PublicEvent) -> None:
        if not self._running:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("⚠️ PublicEvent queue full - dropping oldest event")
            try:
                _ = self._queue.get_nowait()
                self._queue.put_nowait(event)
            except Exception:
                pass

    async def _worker(self) -> None:
        while self._running:
            event = await self._queue.get()
            try:
                await asyncio.to_thread(self._post_json_sync, event.to_payload())
            except Exception as e:
                logger.warning("⚠️ PublicEvent 전송 실패(무시): %s", e)
            finally:
                self._queue.task_done()

    def _post_json_sync(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self.webhook_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Public-Event-Token": self.token,
            },
        )
        with request.urlopen(req, timeout=5) as resp:
            _ = resp.read()


def build_public_event(
    signal: str,
    confidence: float,
    risk_level: str,
    active_character_id: str,
    metrics: Optional[Dict[str, Any]] = None,
) -> PublicEvent:
    direction = "NEUTRAL"
    sig = str(signal or "").upper()
    if sig == "BUY":
        direction = "BUY"
    elif sig == "SELL":
        direction = "SELL"
    reason = f"confidence={float(confidence or 0.0):.2f}, risk={str(risk_level).upper()}"
    metrics = metrics or {}
    return PublicEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_character_id=str(active_character_id or "ox_guard"),
        risk_level=str(risk_level or "SAFE").upper(),
        public_signal_direction=direction,
        abstract_reason=reason,
        position_symbol=metrics.get("position_symbol"),
        position_side=metrics.get("position_side"),
        position_size=metrics.get("position_size"),
        unrealized_pnl_usdt=metrics.get("unrealized_pnl_usdt"),
        realized_24h_usdt=metrics.get("realized_24h_usdt"),
        pnl_24h_type=metrics.get("pnl_24h_type"),
        balance_total_usdt=metrics.get("balance_total_usdt"),
        balance_available_usdt=metrics.get("balance_available_usdt"),
    )

