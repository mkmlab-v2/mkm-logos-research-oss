#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Public Event Gateway (MVP)

Endpoints:
- POST /api/public-events/ingest  : receive sanitized event from n8n/bridge
- GET  /api/public-events/latest  : return latest event for dashboard polling
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

HOST = os.getenv("PUBLIC_EVENT_GATEWAY_HOST", "0.0.0.0")
PORT = int(os.getenv("PUBLIC_EVENT_GATEWAY_PORT", "8788"))
API_TOKEN = os.getenv("PUBLIC_EVENT_GATEWAY_TOKEN", "").strip()
ALLOW_ORIGIN = os.getenv("PUBLIC_EVENT_GATEWAY_ALLOW_ORIGIN", "*")
# Optional: require HMAC-SHA256 on GET /api/public-events/latest (Vercel → Tunnel → localhost).
GET_HMAC_SECRET = os.getenv("PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET", "").strip()
HMAC_MAX_SKEW_SEC = int(os.getenv("PUBLIC_EVENT_GATEWAY_HMAC_MAX_SKEW_SEC", "300"))
_ALLOWED_CHARACTER_IDS = {
    "rat_arbitrage",
    "ox_guard",
    "tiger_shield",
    "rabbit_scalper",
    "dragon_quant",
    "snake_hedger",
    "horse_trend",
    "sheep_yield",
    "monkey_momentum",
    "rooster_oracle",
    "dog_sentinel",
    "pig_accumulator",
    "demo_guard",
    "unknown_guard",
    "bull_alpha",
    "bear_shield",
}

# If this file is deployed outside the repo tree (e.g., /opt/jemaai), fall back safely.
_self = Path(__file__).resolve()
_fallback_root = _self.parent
try:
    _repo_root = _self.parents[4]
except IndexError:
    _repo_root = _fallback_root
WORKSPACE_ROOT = Path(os.getenv("PUBLIC_EVENT_GATEWAY_WORKSPACE_ROOT", str(_repo_root)))
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


def _source_priority(source: str) -> int:
    s = str(source or "").strip().lower()
    if s == "ops_showroom_bundle_v1":
        return 100
    if s == "ops_e2e_smoke":
        return 90
    if s == "linux_runtime_heartbeat":
        return 10
    return 50


def _merge_event_by_priority(current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    current_src = str(current.get("source") or "")
    incoming_src = str(incoming.get("source") or "")
    current_pri = _source_priority(current_src)
    incoming_pri = _source_priority(incoming_src)

    # Same or higher priority: allow full replacement.
    if incoming_pri >= current_pri:
        return incoming

    # Lower priority (e.g. heartbeat): keep rich narrative fields from higher-priority event.
    merged = dict(current)

    # Keep liveness/timing signals updated, but preserve identity/source
    # from the higher-priority event to avoid context downgrade.
    merged["timestamp"] = incoming.get("timestamp", current.get("timestamp"))
    merged["event_id"] = current.get("event_id")
    merged["source"] = current_src
    merged["schema_version"] = incoming.get("schema_version", current.get("schema_version"))
    merged["system_status"] = incoming.get("system_status", current.get("system_status", "online"))

    # Only allow these fields to be updated from low-priority payload if currently missing.
    for key in (
        "active_character_id",
        "risk_level",
        "public_signal_direction",
        "abstract_reason",
        "active_strategies_count",
        "delayed_metrics",
        "direction_abstract",
        "disclaimer_ref",
        "last_ok_utc",
        "showroom_display_mode",
        "showroom_ticker_key",
        "showroom_reaction_line_ids",
    ):
        if key not in merged or merged.get(key) in (None, "", {}):
            merged[key] = incoming.get(key, merged.get(key))

    return merged


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


def build_public_event_get_hmac_signature(secret: str, timestamp_str: str, method: str, path: str) -> str:
    """Canonical string: timestamp\\nMETHOD\\nPATH\\n — same as Vercel server-side signer."""
    msg = f"{timestamp_str}\n{method.upper()}\n{path}\n"
    return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_public_event_get_hmac(
    secret: str,
    headers: Any,
    method: str,
    path: str,
    *,
    now_ts: int | None = None,
    max_skew_sec: int | None = None,
) -> bool:
    """Validate x-mkm-timestamp + x-mkm-signature for read-only GET."""
    if not secret:
        return True
    skew = int(max_skew_sec if max_skew_sec is not None else HMAC_MAX_SKEW_SEC)
    now = int(now_ts if now_ts is not None else time.time())

    def _hdr(name: str) -> str:
        # http.client.HTTPMessage / email.message.Message: get() is case-insensitive for field names.
        try:
            v = headers.get(name)
            return str(v).strip() if v is not None else ""
        except Exception:
            return ""

    ts_raw = _hdr("x-mkm-timestamp")
    sig_received = _hdr("x-mkm-signature").lower()
    if not ts_raw or not sig_received:
        return False
    try:
        ts_int = int(ts_raw)
    except ValueError:
        return False
    if abs(now - ts_int) > skew:
        return False
    expected = build_public_event_get_hmac_signature(secret, ts_raw, method, path)
    return hmac.compare_digest(expected.lower(), sig_received)


def _sanitize_character_id(raw: Any) -> str:
    cid = str(raw or "").strip().lower()
    if not cid:
        return "unknown_guard"
    if cid in _ALLOWED_CHARACTER_IDS:
        return cid
    if "bull" in cid or "attack" in cid:
        return "bull_alpha"
    if "bear" in cid or "shield" in cid or "guard" in cid:
        return "bear_shield"
    return "unknown_guard"


class PublicEventHandler(BaseHTTPRequestHandler):
    server_version = "PublicEventGateway/1.0"

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", ALLOW_ORIGIN)
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Public-Event-Token, X-Mkm-Timestamp, X-Mkm-Signature",
        )
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
            if GET_HMAC_SECRET and not verify_public_event_get_hmac(
                GET_HMAC_SECRET,
                self.headers,
                "GET",
                parsed.path,
            ):
                self._send_json(401, {"ok": False, "error": "unauthorized"})
                return
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
        # Guardrail: normalize active_character_id to whitelisted/public-safe IDs.
        data["active_character_id"] = _sanitize_character_id(data.get("active_character_id"))

        with _state_lock:
            global _latest_event
            _latest_event = _merge_event_by_priority(_latest_event, data)
            _save_state(_latest_event)

        self._send_json(200, {"ok": True, "event_id": data.get("event_id")})


def run() -> None:
    _load_state()
    server = ThreadingHTTPServer((HOST, PORT), PublicEventHandler)
    print(f"[public-event-gateway] listening on http://{HOST}:{PORT}")
    print("[public-event-gateway] GET  /api/public-events/latest")
    print("[public-event-gateway] POST /api/public-events/ingest")
    if GET_HMAC_SECRET:
        print("[public-event-gateway] GET HMAC auth: ENABLED (set PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET)")
    else:
        print("[public-event-gateway] GET HMAC auth: disabled (no PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET)")
    server.serve_forever()


if __name__ == "__main__":
    run()
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.6, K:0.9, M:0.5}
# Balance: 89
# Purpose: Ingest and serve latest public event for MVP dashboard
# Keywords: http server, webhook, public event, mvp, gateway
