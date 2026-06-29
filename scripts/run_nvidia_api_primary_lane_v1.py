#!/usr/bin/env python3
"""
NVIDIA API primary lane — Nemotron/70B via NIM instead of local WSL train.

Solves: 16GB local 30B QLoRA failure, missing Innovation Lab GPU (inference now).
Does NOT fine-tune; use Innovation Lab when accepted for train credits.
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
REGISTRY = ROOT / "docs/final/artifacts/nvidia_nim_model_registry_v1.json"
OUT = ROOT / "reports/nvidia_api_primary_lane_v1_latest.json"
ENV_PATH = ROOT / ".env"
BASE = "https://integrate.api.nvidia.com/v1"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _key() -> str | None:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NGC_API_KEY")


def _list_model_ids(key: str) -> set[str]:
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


def _model_candidates(registry: dict, available: set[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for mid in [registry.get("primary_chat"), *(registry.get("fallback_chat") or [])]:
        if mid and mid in available and mid not in seen:
            seen.add(mid)
            out.append(mid)
    env = os.getenv("NVIDIA_NIM_MODEL")
    if env and env in available and env not in seen:
        out.append(env)
    for mid in ("meta/llama-3.3-70b-instruct", "meta/llama-3.1-70b-instruct", "meta/llama-3.1-8b-instruct"):
        if mid in available and mid not in seen:
            out.append(mid)
    if not out:
        raise RuntimeError("no_chat_model_in_catalog")
    return out


def _chat(key: str, model: str, prompt: str, max_tokens: int) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
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
        err = e.read().decode("utf-8", errors="replace")[:800]
        return {"ok": False, "http_status": e.code, "model": model, "error": err}


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    key = _key()
    if not key:
        print("missing NVIDIA_API_KEY / NGC_API_KEY", file=sys.stderr)
        return 2

    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    available = _list_model_ids(key)
    candidates = _model_candidates(registry, available)

    prompt = (
        "한국어로만 답하라. [HYPO] B-track 연구용.\n"
        "과제: 로컬 RTX 16GB에서 30B QLoRA 학습이 실패할 때, "
        "NVIDIA NIM API로 Nemotron급 추론을 대체하는 운영 원칙을 4개 불릿으로 쓰라. "
        "마지막 줄에 'API로 해결: 추론=NIM, 파인튜닝=Innovation Lab 대기' 한 문장.\n"
        "가격·매매 GO 금지."
    )

    attempts: list[dict] = []
    chat: dict = {"ok": False, "error": "no_model_succeeded"}
    model = candidates[0]
    for model in candidates:
        chat = _chat(key, model, prompt, args.max_tokens)
        attempts.append({"model": model, "ok": chat.get("ok"), "http_status": chat.get("http_status")})
        if chat.get("ok"):
            break

    finished = datetime.now(timezone.utc).isoformat()
    doc = {
        "schema": "nvidia_api_primary_lane_v1",
        "finished_at_utc": finished,
        "lane": "b_track_research_only",
        "research_only": True,
        "solution": "nvidia_api_nim_inference",
        "wsl_30b_qlora": "skipped_use_api",
        "registry_path": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
        "model_selected": model,
        "model_attempts": attempts,
        "nemotron_70_catalog_but_404": any(
            a.get("model") == "nvidia/llama-3.1-nemotron-70b-instruct" and a.get("http_status") == 404
            for a in attempts
        ),
        "catalog_size": len(available),
        "chat": chat,
        "next_for_finetune": "Innovation Lab + Brev when acceptance email",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if chat.get("ok"):
        print(f"[model] {model}")
        print(chat["text"])
        print(f"\n[ok] {args.out_json}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
