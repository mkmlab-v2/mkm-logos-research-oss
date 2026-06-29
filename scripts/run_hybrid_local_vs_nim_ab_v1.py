#!/usr/bin/env python3
"""
Recommended hybrid A/B: local Ollama llama3.1:8b vs NIM meta/llama-3.3-70b-instruct.

Same prompt, timing, side-by-side report. B-track / research_only only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_OUT = ROOT / "reports/hybrid_local_vs_nim_ab_v1_latest.json"
OLLAMA_MODEL = "llama3.1:8b"
NIM_MODEL = "meta/llama-3.3-70b-instruct"
DEFAULT_PROMPT = (
    "한국어로만 답하라 [HYPO]. LLM 하이브리드 운영 초안 3불릿: "
    "(1) 로컬 GPU 8B 파라미터 언어모델(Ollama)에 적합한 작업 "
    "(2) 클라우드 70B NIM API에 적합한 작업 "
    "(3) 둘을 섞을 때 주의. 네트워크 대역폭·8bit 양자화 이야기 금지. "
    "투자·매매 조언 금지."
)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _ollama_host() -> str:
    return (os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/").replace("/v1", "")


def _api_key() -> str | None:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NGC_API_KEY")


def _ollama_generate(model: str, prompt: str, timeout: int) -> dict:
    host = _ollama_host()
    url = f"{host}/api/generate"
    body = {"model": model, "prompt": prompt, "stream": False}
    t0 = time.perf_counter()
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        elapsed = time.perf_counter() - t0
        text = (payload.get("response") or "").strip()
        return {
            "ok": bool(text),
            "backend": "ollama",
            "model": model,
            "elapsed_sec": round(elapsed, 2),
            "eval_duration_ns": payload.get("eval_duration"),
            "load_duration_ns": payload.get("load_duration"),
            "text": text,
            "text_len": len(text),
        }
    except Exception as e:
        return {
            "ok": False,
            "backend": "ollama",
            "model": model,
            "elapsed_sec": round(time.perf_counter() - t0, 2),
            "error": str(e),
        }


def _nim_chat(model: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    key = _api_key()
    if not key:
        return {"ok": False, "backend": "nim", "error": "missing NVIDIA_API_KEY"}
    base = (os.getenv("NVIDIA_NIM_BASE_URL") or "https://integrate.api.nvidia.com/v1").rstrip("/")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "stream": False,
    }
    t0 = time.perf_counter()
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        elapsed = time.perf_counter() - t0
        choices = payload.get("choices") or []
        text = ""
        if choices and isinstance(choices[0], dict):
            text = ((choices[0].get("message") or {}).get("content") or "").strip()
        return {
            "ok": bool(text),
            "backend": "nim",
            "model": model,
            "http_status": resp.status,
            "elapsed_sec": round(elapsed, 2),
            "usage": payload.get("usage"),
            "text": text,
            "text_len": len(text),
        }
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:500]
        return {
            "ok": False,
            "backend": "nim",
            "model": model,
            "http_status": e.code,
            "elapsed_sec": round(time.perf_counter() - t0, 2),
            "error": err,
        }
    except Exception as e:
        return {
            "ok": False,
            "backend": "nim",
            "model": model,
            "elapsed_sec": round(time.perf_counter() - t0, 2),
            "error": str(e),
        }


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--ollama-model", default=OLLAMA_MODEL)
    ap.add_argument("--nim-model", default=NIM_MODEL)
    ap.add_argument("--max-tokens", type=int, default=450)
    ap.add_argument("--ollama-timeout-sec", type=int, default=300)
    ap.add_argument("--nim-timeout-sec", type=int, default=180)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = {
        "schema": "hybrid_local_vs_nim_ab_v1",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "b_track_research_only",
        "recommended_routing": {
            "local_ollama": args.ollama_model,
            "cloud_nim": args.nim_model,
            "embed_local": "nomic-embed-text:latest",
        },
        "prompt_chars": len(args.prompt),
        "runs": [],
    }

    local = _ollama_generate(args.ollama_model, args.prompt, args.ollama_timeout_sec)
    doc["runs"].append(local)
    nim = _nim_chat(args.nim_model, args.prompt, args.max_tokens, args.nim_timeout_sec)
    doc["runs"].append(nim)

    doc["ok"] = local.get("ok") and nim.get("ok")
    if doc["ok"]:
        doc["latency_ratio_nim_over_local"] = round(
            nim["elapsed_sec"] / max(local["elapsed_sec"], 0.01), 2
        )
        doc["len_ratio_nim_over_local"] = round(
            nim["text_len"] / max(local["text_len"], 1), 2
        )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("=== LOCAL", args.ollama_model, f"({local.get('elapsed_sec')}s) ===")
    print(local.get("text", local.get("error", ""))[:2000])
    print("\n=== NIM", args.nim_model, f"({nim.get('elapsed_sec')}s) ===")
    print(nim.get("text", nim.get("error", ""))[:2000])
    print(f"\n[report] {args.out_json}")
    return 0 if doc["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
