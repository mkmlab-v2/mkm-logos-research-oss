#!/usr/bin/env python3
"""[HYPO] Edge Encoder cross-process HTTP roundtrip vs in-process TestClient."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]


def _post_json(url: str, payload: dict[str, Any], *, timeout: float = 60) -> tuple[int, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(raw) if raw.strip() else raw
        except json.JSONDecodeError:
            parsed = raw[:500]
        return exc.code, parsed


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_health(base_url: str, *, timeout_s: float = 20) -> bool:
    deadline = time.time() + timeout_s
    url = f"{base_url.rstrip('/')}/health"
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


@dataclass
class EphemeralV2Stub:
    port: int
    base_url: str
    _proc: subprocess.Popen[Any] | None = None

    @classmethod
    def start(cls, *, port: int | None = None, workspace_root: Path = ROOT) -> EphemeralV2Stub:
        chosen = port or _pick_free_port()
        base_url = f"http://127.0.0.1:{chosen}"
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "scripts.compression_token_api_v2_stub:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(chosen),
                "--log-level",
                "warning",
            ],
            cwd=str(workspace_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        inst = cls(port=chosen, base_url=base_url, _proc=proc)
        if not _wait_health(base_url):
            inst.stop()
            raise RuntimeError(f"v2 stub failed to become healthy on {base_url}")
        return inst

    def stop(self) -> None:
        if self._proc is None:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=3)
        self._proc = None


@contextmanager
def ephemeral_v2_stub(*, port: int | None = None, workspace_root: Path = ROOT) -> Iterator[EphemeralV2Stub]:
    server = EphemeralV2Stub.start(port=port, workspace_root=workspace_root)
    try:
        yield server
    finally:
        server.stop()


def roundtrip_wire_testclient(
    wire: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    from scripts.edge_encoder_sdk_v1_lib import (
        compression_packet_fingerprint,
        wire_compress_request_body,
    )
    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import app
    from scripts.coord_anatomy_overlay_wire_v1_lib import materialize_coord_wire

    client = TestClient(app)
    cr = client.post("/v2/compress", json=wire_compress_request_body(wire))
    out: dict[str, Any] = {"transport": "testclient", "compress_status": cr.status_code}
    if cr.status_code != 200:
        out["ok"] = False
        out["error"] = cr.text[:300]
        return out
    pkt = cr.json().get("compression_packet") or {}
    out["packet_fingerprint"] = compression_packet_fingerprint(pkt)
    er = client.post("/v2/expand", json={"compression_packet": pkt, "decode_mode": "codebook_only"})
    out["expand_status"] = er.status_code
    if er.status_code != 200:
        out["ok"] = False
        out["error"] = er.text[:300]
        return out
    out["expand_text"] = er.json().get("text") or ""
    render = materialize_coord_wire(wire, workspace_root=workspace_root)
    out["local_render_ok"] = bool(render.get("base_sha256_match"))
    out["ok"] = out["local_render_ok"]
    return out


def roundtrip_wire_http(
    wire: dict[str, Any],
    base_url: str,
    *,
    workspace_root: Path = ROOT,
) -> dict[str, Any]:
    from scripts.coord_anatomy_overlay_wire_v1_lib import materialize_coord_wire
    from scripts.edge_encoder_sdk_v1_lib import (
        compression_packet_fingerprint,
        wire_compress_request_body,
    )

    base = base_url.rstrip("/")
    status, body = _post_json(f"{base}/v2/compress", wire_compress_request_body(wire))
    out: dict[str, Any] = {"transport": "http", "compress_status": status, "base_url": base}
    if status != 200 or not isinstance(body, dict):
        out["ok"] = False
        out["error"] = str(body)[:300]
        return out
    pkt = body.get("compression_packet") or {}
    out["packet_fingerprint"] = compression_packet_fingerprint(pkt)
    estatus, ebody = _post_json(
        f"{base}/v2/expand",
        {"compression_packet": pkt, "decode_mode": "codebook_only"},
    )
    out["expand_status"] = estatus
    if estatus != 200 or not isinstance(ebody, dict):
        out["ok"] = False
        out["error"] = str(ebody)[:300]
        return out
    out["expand_text"] = ebody.get("text") or ""
    render = materialize_coord_wire(wire, workspace_root=workspace_root)
    out["local_render_ok"] = bool(render.get("base_sha256_match"))
    out["ok"] = out["local_render_ok"]
    return out


def check_cross_process_determinism(
    wire: dict[str, Any],
    *,
    workspace_root: Path = ROOT,
    base_url: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    tc = roundtrip_wire_testclient(wire, workspace_root=workspace_root)
    if not tc.get("ok"):
        errors.append(f"testclient roundtrip failed: {tc.get('error', tc)}")

    if base_url:
        http = roundtrip_wire_http(wire, base_url, workspace_root=workspace_root)
        server_mode = "external"
    else:
        with ephemeral_v2_stub(workspace_root=workspace_root) as srv:
            http = roundtrip_wire_http(wire, srv.base_url, workspace_root=workspace_root)
            server_mode = f"ephemeral:{srv.port}"

    if not http.get("ok"):
        errors.append(f"http roundtrip failed: {http.get('error', http)}")

    if tc.get("packet_fingerprint") and http.get("packet_fingerprint"):
        if tc["packet_fingerprint"] != http["packet_fingerprint"]:
            errors.append("cross_process: compression_packet fingerprint mismatch")
    if tc.get("expand_text") is not None and http.get("expand_text") is not None:
        if tc["expand_text"] != http["expand_text"]:
            errors.append("cross_process: expand text mismatch")

    summary = {
        "server_mode": server_mode,
        "testclient_ok": bool(tc.get("ok")),
        "http_ok": bool(http.get("ok")),
        "fingerprint_match": tc.get("packet_fingerprint") == http.get("packet_fingerprint"),
        "expand_text_match": tc.get("expand_text") == http.get("expand_text"),
        "original_bulk_sent": False,
    }
    return errors, summary
