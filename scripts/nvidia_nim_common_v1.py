"""Shared NIM helpers (no secrets in logs)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/nvidia_nim_model_registry_v1.json"
BASE = "https://integrate.api.nvidia.com/v1"


def api_key() -> str | None:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NGC_API_KEY")


def list_model_ids(key: str) -> set[str]:
    req = urllib.request.Request(
        f"{BASE}/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    ids: set[str] = set()
    for m in data.get("data") or []:
        if isinstance(m, dict) and m.get("id"):
            ids.add(m["id"])
        elif isinstance(m, str):
            ids.add(m)
    return ids


def chat_candidates(registry: dict, available: set[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for mid in [registry.get("primary_chat"), *(registry.get("fallback_chat") or [])]:
        if mid and mid in available and mid not in seen:
            seen.add(mid)
            out.append(mid)
    env = os.getenv("NVIDIA_NIM_MODEL")
    if env and env in available and env not in seen:
        out.append(env)
    for mid in ("meta/llama-3.3-70b-instruct", "meta/llama-3.1-8b-instruct"):
        if mid in available and mid not in seen:
            out.append(mid)
    return out


def chat_with_fallback(key: str, registry: dict, prompt: str, max_tokens: int) -> tuple[dict, list[dict]]:
    available = list_model_ids(key)
    attempts: list[dict] = []
    chat: dict = {"ok": False, "error": "no_model_succeeded"}
    model = ""
    for model in chat_candidates(registry, available):
        chat = _chat_once(key, model, prompt, max_tokens)
        attempts.append({"model": model, "ok": chat.get("ok"), "http_status": chat.get("http_status")})
        if chat.get("ok"):
            break
    return chat, attempts


def _chat_once(key: str, model: str, prompt: str, max_tokens: int) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.35,
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = ""
        ch = payload.get("choices") or []
        if ch:
            text = ((ch[0].get("message") or {}).get("content") or "").strip()
        return {
            "ok": bool(text),
            "http_status": resp.status,
            "model": model,
            "text": text,
            "usage": payload.get("usage"),
        }
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "http_status": e.code,
            "model": model,
            "error": e.read().decode("utf-8", errors="replace")[:800],
        }
    except Exception as e:
        return {"ok": False, "model": model, "error": str(e)}
