#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Public Event Gateway (MVP)

Endpoints:
- POST /api/public-events/ingest  : receive sanitized event from n8n/bridge
- GET  /api/public-events/latest  : return latest event for dashboard polling
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

HOST = os.getenv("PUBLIC_EVENT_GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("PUBLIC_EVENT_GATEWAY_PORT", "8788"))
API_TOKEN = os.getenv("PUBLIC_EVENT_GATEWAY_TOKEN", "").strip()
ALLOW_ORIGIN = os.getenv("PUBLIC_EVENT_GATEWAY_ALLOW_ORIGIN", "*")

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_STATE_PATH = WORKSPACE_ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "public" / "public_event_latest.json"
STATE_PATH = Path(os.getenv("PUBLIC_EVENT_GATEWAY_STATE_PATH", str(DEFAULT_STATE_PATH)))

_state_lock = threading.Lock()
_latest_event: Dict[str, Any] = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "active_character_id": "unknown_guard",
    "risk_level": "WARNING",
    "public_signal_direction": "HOLD",
    "abstract_reason": "No event ingested yet.",
    "schema_version": "public-event.v1",
    "event_id": "bootstrap",
    "source": "public-event-gateway",
}


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> None:
    global _latest_event
    if not STATE_PATH.is_file():
        return
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            _latest_event = payload
    except Exception:
        pass


def _save_state(payload: Dict[str, Any]) -> None:
    _ensure_parent(STATE_PATH)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_valid_event(payload: Dict[str, Any]) -> bool:
    required = [
        "timestamp",
        "active_character_id",
        "risk_level",
        "public_signal_direction",
        "abstract_reason",
        "schema_version",
        "event_id",
        "source",
    ]
    return all(k in payload for k in required)


class PublicEventHandler(BaseHTTPRequestHandler):
    server_version = "PublicEventGateway/1.0"

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Public-Event-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _authorized(self) -> bool:
        if not API_TOKEN:
            return True
        received = (self.headers.get("X-Public-Event-Token") or "").strip()
        return received == API_TOKEN

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/public-events/latest":
            with _state_lock:
                payload = dict(_latest_event)
            self._send_json(200, payload)
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/public-events/ingest":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        if not self._authorized():
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return

        data = self._read_json_body()
        if not data or not _is_valid_event(data):
            self._send_json(400, {"ok": False, "error": "invalid_payload"})
            return

        with _state_lock:
            global _latest_event
            _latest_event = data
            _save_state(_latest_event)

        self._send_json(200, {"ok": True, "event_id": data.get("event_id")})


def run() -> None:
    _load_state()
    server = ThreadingHTTPServer((HOST, PORT), PublicEventHandler)
    print(f"[public-event-gateway] listening on http://{HOST}:{PORT}")
    print("[public-event-gateway] GET  /api/public-events/latest")
    print("[public-event-gateway] POST /api/public-events/ingest")
    server.serve_forever()


if __name__ == "__main__":
    run()
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.6, K:0.9, M:0.5}
# Balance: 89
# Purpose: Ingest and serve latest public event for MVP dashboard
# Keywords: http server, webhook, public event, mvp, gateway
