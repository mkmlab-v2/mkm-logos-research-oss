#!/usr/bin/env python3
"""B-track v0: OpenAI-compatible chat shim with coding-proxy compress (research_only).

Run: py -m uvicorn scripts.cursor_chat_shim_v1:app --host 127.0.0.1 --port 8011
Dry-run (no upstream): MKM_CHAT_SHIM_DRY_RUN=1
"""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from scripts.core.billing_meter import append_meter_event  # noqa: E402
from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface  # noqa: E402
from scripts.run_cursor_coding_compress_bench_v1 import (  # noqa: E402
    _load_lane_intensity,
    _selected_profile,
    _token_in,
)

DEFAULT_HARDENING = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"

app = FastAPI(title="MKM Cursor Chat Shim v0", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool | None = False


def _ensure_hardening_env() -> None:
    if not os.environ.get("COMPRESSION_HARDENING_CONFIG_PATH", "").strip():
        os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(DEFAULT_HARDENING)
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()


def _dry_run_enabled() -> bool:
    return os.environ.get("MKM_CHAT_SHIM_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


def _compress_content(content: str, *, role: str) -> tuple[str, dict[str, Any]]:
    if role not in {"system", "user"}:
        return content, {"skipped": "role_not_compressible"}
    if _token_in(content) < 12:
        return content, {"skipped": "short_content"}
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(DEFAULT_HARDENING)
    lane = "agent_rules_excerpt" if role == "system" else "long_multifile"
    out = coding_proxy_compress_surface(content, profile, lane=lane, lane_intensity=lane_intensity)
    surface = str(out.get("surface") or content)
    return surface, {
        "proxy_path": out.get("proxy_path"),
        "structured_preserve": out.get("structured_preserve"),
        "token_in": out.get("raw_tokens") or _token_in(content),
        "token_out": out.get("compressed_tokens") or _token_in(surface),
        "saving_rate": out.get("global_token_saving_rate"),
    }


def _transform_messages(messages: list[ChatMessage]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _ensure_hardening_env()
    out_msgs: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for i, m in enumerate(messages):
        content = m.content or ""
        new_content, flags = _compress_content(content, role=m.role)
        out_msgs.append({"role": m.role, "content": new_content})
        if flags.get("skipped"):
            audit.append({"index": i, "role": m.role, **flags})
        else:
            audit.append({"index": i, "role": m.role, **flags})
    return out_msgs, audit


def _estimate_tokens(text: str) -> int:
    return max(1, _token_in(text))


def _dry_response(model: str | None, audit: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-shim-dry-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "model": model or "mkm-shim-dry-run",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "[MKM_SHIM_DRY_RUN] upstream skipped"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "mkm_shim_integrity": {
            "dry_run": True,
            "research_only": True,
            "message_audit": audit,
        },
    }


def _forward_upstream(body: dict[str, Any]) -> dict[str, Any]:
    base = os.environ.get("MKM_CHAT_SHIM_UPSTREAM_BASE_URL", "").strip().rstrip("/")
    key = os.environ.get("MKM_CHAT_SHIM_UPSTREAM_API_KEY", "").strip()
    if not base or not key:
        raise RuntimeError("upstream_not_configured")

    if base.rstrip("/").endswith("/openai"):
        url = f"{base.rstrip('/')}/chat/completions"
    elif base.endswith("/v1"):
        url = f"{base}/chat/completions"
    else:
        url = f"{base}/v1/chat/completions"

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _meter_from_audit(audit: list[dict[str, Any]], *, client_id: str | None) -> None:
    tin = 0
    tout = 0
    for row in audit:
        if row.get("skipped"):
            continue
        tin += int(row.get("token_in") or 0)
        tout += int(row.get("token_out") or 0)
    if tin <= 0:
        return
    try:
        append_meter_event(
            {
                "sla_track": "chat_shim_btrack",
                "tokens_before": tin,
                "tokens_after": max(1, tout),
                "client_request_id": client_id,
                "notes": "cursor_chat_shim_v1_compress",
            }
        )
    except Exception:
        pass


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "schema": "cursor_chat_shim_v0",
        "research_only": True,
        "dry_run": _dry_run_enabled(),
        "upstream_configured": bool(os.environ.get("MKM_CHAT_SHIM_UPSTREAM_BASE_URL", "").strip()),
    }


@app.post("/v1/chat/completions")
def chat_completions(body: ChatCompletionRequest, request: Request) -> dict[str, Any]:
    if body.stream:
        return {
            "error": {
                "message": "stream not supported in v0 shim",
                "type": "mkm_shim_unsupported",
            }
        }

    msgs, audit = _transform_messages(body.messages)
    upstream_body: dict[str, Any] = {
        "model": body.model or os.environ.get("MKM_CHAT_SHIM_UPSTREAM_MODEL", "gpt-4.1-mini"),
        "messages": msgs,
    }
    if body.temperature is not None:
        upstream_body["temperature"] = body.temperature
    if body.max_tokens is not None:
        upstream_body["max_tokens"] = body.max_tokens

    client_id = request.headers.get("x-request-id") or request.headers.get("x-client-request-id")

    if _dry_run_enabled():
        resp = _dry_response(body.model, audit)
    else:
        try:
            resp = _forward_upstream(upstream_body)
        except (urllib.error.URLError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
            return {
                "error": {
                    "message": str(exc),
                    "type": "mkm_shim_upstream_error",
                },
                "mkm_shim_integrity": {"message_audit": audit, "research_only": True},
            }
        if isinstance(resp, dict):
            resp.setdefault("mkm_shim_integrity", {})
            if isinstance(resp["mkm_shim_integrity"], dict):
                resp["mkm_shim_integrity"].update(
                    {"research_only": True, "message_audit": audit, "dry_run": False}
                )

    _meter_from_audit(audit, client_id=client_id)
    return resp
