#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVIDIA NIM (integrate.api.nvidia.com) — OpenAI-compatible chat smoke / one-shot query.

Auth: NVIDIA_API_KEY or NGC_API_KEY from C:\\workspace\\.env (never print secrets).
Lane: B-track / operator tooling only — not Track A, not live trading, not MS headline proof.

Examples:
  py scripts/nvidia_nim_chat_v1.py smoke
  py scripts/nvidia_nim_chat_v1.py chat --prompt "Two bullets: local GPU vs NIM API roles."
  py scripts/nvidia_nim_chat_v1.py list-models
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"
DEFAULT_OUT = ROOT / "reports" / "nvidia_nim_chat_v1_latest.json"
DEFAULT_SMOKE_PROMPT = (
    "Reply in exactly 2 short bullets (Korean): "
    "(1) what NVIDIA NIM API is for when the PC has 16GB VRAM; "
    "(2) one limitation of cloud NIM vs local GPU. No marketing tone."
)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _api_key() -> str | None:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NGC_API_KEY")


def _base_url() -> str:
    return (os.getenv("NVIDIA_NIM_BASE_URL") or DEFAULT_BASE).rstrip("/")


def _request(
    method: str,
    path: str,
    *,
    api_key: str,
    body: dict | None = None,
    timeout: int = 120,
) -> tuple[int, dict | list | str]:
    url = f"{_base_url()}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, err


def cmd_list_models(api_key: str) -> dict:
    status, payload = _request("GET", "/models", api_key=api_key)
    ids: list[str] = []
    if status == 200 and isinstance(payload, dict):
        for row in payload.get("data") or []:
            if isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]))
    return {
        "http_status": status,
        "model_count": len(ids),
        "sample_ids": ids[:12],
    }


def cmd_chat(
    api_key: str,
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    status, payload = _request("POST", "/chat/completions", api_key=api_key, body=body)
    out: dict = {"http_status": status, "model": model, "prompt_chars": len(prompt)}
    if status == 200 and isinstance(payload, dict):
        choices = payload.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = (choices[0].get("message") or {}).get("content")
            out["assistant_text"] = (msg or "").strip()
        usage = payload.get("usage")
        if isinstance(usage, dict):
            out["usage"] = usage
        out["ok"] = bool(out.get("assistant_text"))
    else:
        out["ok"] = False
        out["error"] = payload if isinstance(payload, (dict, str)) else str(payload)
    return out


def _write_report(doc: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    _load_dotenv()
    api_key = _api_key()
    if not api_key:
        print("NGC_API_KEY or NVIDIA_API_KEY required in .env", file=sys.stderr)
        return 1

    ap = argparse.ArgumentParser(description="NVIDIA NIM chat v1")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_smoke = sub.add_parser("smoke", help="Default short chat + models count")
    p_smoke.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p_smoke.add_argument("--model", default=os.getenv("NVIDIA_NIM_MODEL") or DEFAULT_MODEL)
    p_smoke.add_argument("--max-tokens", type=int, default=256)

    p_chat = sub.add_parser("chat", help="Single user prompt")
    p_chat.add_argument("--prompt", required=True)
    p_chat.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    p_chat.add_argument("--model", default=os.getenv("NVIDIA_NIM_MODEL") or DEFAULT_MODEL)
    p_chat.add_argument("--max-tokens", type=int, default=1024)
    p_chat.add_argument("--temperature", type=float, default=0.4)

    p_list = sub.add_parser("list-models", help="List first N model ids")
    p_list.add_argument("--out-json", type=Path, default=DEFAULT_OUT)

    args = ap.parse_args()
    finished = datetime.now(timezone.utc).isoformat()

    if args.cmd == "list-models":
        doc = {
            "schema": "nvidia_nim_chat_v1",
            "mode": "list-models",
            "finished_at_utc": finished,
            "base_url": _base_url(),
            "lane": "b_track_operator_tooling",
            "models": cmd_list_models(api_key),
        }
        _write_report(doc, args.out_json)
        print(json.dumps(doc["models"], indent=2, ensure_ascii=False))
        return 0 if doc["models"].get("http_status") == 200 else 3

    prompt = DEFAULT_SMOKE_PROMPT if args.cmd == "smoke" else args.prompt
    chat_result = cmd_chat(
        api_key,
        prompt=prompt,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=getattr(args, "temperature", 0.3),
    )
    models_meta = cmd_list_models(api_key)
    doc = {
        "schema": "nvidia_nim_chat_v1",
        "mode": args.cmd,
        "finished_at_utc": finished,
        "base_url": _base_url(),
        "lane": "b_track_operator_tooling",
        "research_only": True,
        "models_catalog": {
            "http_status": models_meta.get("http_status"),
            "model_count": models_meta.get("model_count"),
        },
        "chat": chat_result,
    }
    _write_report(doc, args.out_json)

    if chat_result.get("ok"):
        print(chat_result.get("assistant_text", ""))
        print(f"\n[ok] report -> {args.out_json}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
