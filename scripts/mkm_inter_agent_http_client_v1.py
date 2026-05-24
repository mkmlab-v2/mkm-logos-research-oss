#!/usr/bin/env python3
"""HTTP client for MKM compression / inter-agent research API (stdlib urllib)."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator


@dataclass
class HttpResponse:
    status_code: int
    body: bytes
    headers: dict[str, str]

    def json(self) -> dict[str, Any]:
        return json.loads(self.body.decode("utf-8"))

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class MkmCompressionHttpClient:
    """Minimal POST/GET client matching runtime adapter protocol."""

    def __init__(self, base_url: str, *, timeout_sec: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def post(self, path: str, **kwargs: Any) -> HttpResponse:
        payload: dict[str, Any] = kwargs.get("json") or {}
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                raw = resp.read()
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                return HttpResponse(status_code=int(resp.status), body=raw, headers=hdrs)
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp else b""
            return HttpResponse(status_code=int(exc.code), body=raw, headers={})

    def get(self, path: str) -> HttpResponse:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            raw = resp.read()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return HttpResponse(status_code=int(resp.status), body=raw, headers=hdrs)


def resolve_inter_agent_http_base_url() -> str | None:
    for key in ("MKM_INTER_AGENT_HTTP_BASE_URL", "MKM_COMPRESSION_API_BASE_URL"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val.rstrip("/")
    return None


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def ephemeral_compression_api_server(
    *,
    host: str = "127.0.0.1",
    startup_timeout_sec: float = 15.0,
) -> Generator[str, None, None]:
    """Start compression_token_api_v2_stub on a free local port (real HTTP, not TestClient)."""
    import uvicorn

    from scripts.compression_token_api_v2_stub import app

    port = _pick_free_port()
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    def _run() -> None:
        server.run()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    base = f"http://{host}:{port}"
    client = MkmCompressionHttpClient(base, timeout_sec=2.0)
    deadline = time.monotonic() + startup_timeout_sec
    last_err: str | None = None
    while time.monotonic() < deadline:
        try:
            r = client.get("/health")
            if r.status_code == 200:
                yield base
                server.should_exit = True
                thread.join(timeout=5.0)
                return
            last_err = f"health_status_{r.status_code}"
        except Exception as exc:
            last_err = f"{type(exc).__name__}:{exc}"
        time.sleep(0.15)
    raise RuntimeError(f"ephemeral_api_not_ready:{last_err}")
