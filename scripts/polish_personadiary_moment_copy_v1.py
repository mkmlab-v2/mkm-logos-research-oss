#!/usr/bin/env python3
"""Optional polish for PersonaDiary moment summaries [HYPO · research_only].

Batch (offline): Ollama optional, Azure fallback when MKM_PERSONADIARY_MOMENT_AZURE_POLISH=1.
Runtime (live API): Azure direct only — Ollama generate skipped (shallow router stays separate).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_TIMEOUT = 45
AZURE_DEFAULT_TIMEOUT = 30

PRESET_QUERIES: dict[str, str] = {
    "meal": "오늘 점심 뭐 먹을까?",
    "weather_fit": "오늘 날씨에 뭐 입을까?",
    "mood": "지금 기분이 가라앉아서 마음을 정리하고 싶어.",
}

SYSTEM_PROMPT = """You polish one Korean sentence for a wellness diary preview.
Rules:
- Output exactly ONE short Korean sentence (max 120 chars).
- Keep factual hints from the input; do not invent menus, weather, or medical facts.
- Warm, calm tone. No emojis.
- No investment, trading, clinical, or prescription advice.
- Tag internally as hypothesis; do not print tags in output."""


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def polish_enabled() -> bool:
    _load_dotenv()
    raw = (os.getenv("MKM_PERSONADIARY_MOMENT_OLLAMA_POLISH") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _host() -> str:
    return (os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/").replace("/v1", "")


def _model() -> str:
    return os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_polished(text: str, *, max_len: int = 140) -> str:
    s = re.sub(r"\[(?:가설|NON_GATING|HYPO)[^\]]*\]", "", text or "")
    s = re.sub(r"\s+", " ", s).strip().strip('"').strip("'")
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def build_polish_user_prompt(*, summary_ko: str, intent: str, query: str) -> str:
    return (
        f"Intent: {intent}\n"
        f"User question: {query.strip()[:200]}\n"
        f"Deterministic draft: {summary_ko.strip()[:300]}\n"
        "Rewrite as one friendly Korean sentence for the user."
    )


def _runtime_polish_flag() -> str:
    _load_dotenv()
    return (os.getenv("MKM_PERSONADIARY_MOMENT_RUNTIME_POLISH") or "auto").strip().lower()


def runtime_polish_explicit_off() -> bool:
    return _runtime_polish_flag() in ("0", "false", "no", "off")


def runtime_polish_explicit_on() -> bool:
    return _runtime_polish_flag() in ("1", "true", "yes", "on")


def _ollama_reachable(timeout_sec: float = 2.0) -> bool:
    host = _host()
    try:
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def runtime_backends_available() -> bool:
    """Runtime polish uses Azure only (no Ollama generate on live path)."""
    _load_dotenv()
    return _azure_env_ok()


def runtime_polish_enabled() -> bool:
    if runtime_polish_explicit_off():
        return False
    if runtime_polish_explicit_on():
        return True
    # auto (default): Azure configured for runtime direct polish
    return runtime_backends_available()


def _azure_env_ok() -> bool:
    _load_dotenv()
    ep = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
    key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
    dep = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
    return bool(ep and key and dep)


def azure_polish_enabled(*, allow_runtime_fallback: bool = False) -> bool:
    _load_dotenv()
    raw = (os.getenv("MKM_PERSONADIARY_MOMENT_AZURE_POLISH") or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return _azure_env_ok()
    if allow_runtime_fallback and runtime_polish_enabled():
        return _azure_env_ok()
    return False


def _azure_timeout_sec() -> int:
    _load_dotenv()
    raw = (os.getenv("AZURE_OPENAI_FETCH_TIMEOUT_MS") or "30000").strip()
    try:
        return max(5, min(120, int(raw) // 1000))
    except ValueError:
        return AZURE_DEFAULT_TIMEOUT


def azure_polish_summary(
    summary_ko: str,
    *,
    intent: str,
    query: str,
    timeout_sec: int | None = None,
) -> tuple[str | None, dict[str, Any]]:
    meta: dict[str, Any] = {
        "lane": "research_only",
        "hypothesis_tier": "B",
        "backend": "azure_openai",
        "applied": False,
    }
    if not summary_ko.strip():
        meta["reason"] = "empty_summary"
        return None, meta
    if not _azure_env_ok():
        meta["reason"] = "azure_env_incomplete"
        return None, meta

    ep = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
    key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
    dep = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
    ver = (os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
    timeout = timeout_sec if timeout_sec is not None else _azure_timeout_sec()
    prompt = build_polish_user_prompt(summary_ko=summary_ko, intent=intent, query=query)
    body = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 120,
        "temperature": 0.35,
    }
    url = f"{ep}/openai/deployments/{dep}/chat/completions?api-version={ver}"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"api-key": key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        choices = payload.get("choices") or []
        content = ""
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            content = str(msg.get("content") or "")
        polished = _clean_polished(content)
        if len(polished) < 8:
            meta["reason"] = "empty_response"
            return None, meta
        meta["applied"] = True
        meta["deployment"] = dep
        meta["polished_at_utc"] = _utc_now()
        return polished, meta
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError) as exc:
        meta["reason"] = str(exc)[:200]
        return None, meta


def polish_summary_with_fallback(
    summary_ko: str,
    *,
    intent: str,
    query: str,
    timeout_sec: int = DEFAULT_TIMEOUT,
    force: bool = False,
    mode: str = "batch",
) -> tuple[str | None, dict[str, Any]]:
    """Polish chain. batch=Ollama→Azure; runtime=Azure direct (Ollama generate skipped)."""
    attempts: list[dict[str, Any]] = []
    if mode == "runtime" and not runtime_polish_enabled():
        return None, {
            "lane": "research_only",
            "hypothesis_tier": "B",
            "backend": "none",
            "applied": False,
            "reason": "runtime_disabled",
            "attempts": attempts,
        }

    try_ollama = mode != "runtime" and (force or polish_enabled())
    if try_ollama:
        polished, ollama_meta = ollama_polish_summary(
            summary_ko,
            intent=intent,
            query=query,
            timeout_sec=min(timeout_sec, 25) if mode == "runtime" else timeout_sec,
            force=force,
        )
        attempts.append({"backend": "ollama", **ollama_meta})
        if polished:
            return polished, {
                "lane": "research_only",
                "hypothesis_tier": "B",
                "backend": "ollama",
                "applied": True,
                "attempts": attempts,
                **{k: v for k, v in ollama_meta.items() if k not in {"backend", "applied"}},
            }

    if azure_polish_enabled(allow_runtime_fallback=(mode == "runtime")):
        polished, azure_meta = azure_polish_summary(
            summary_ko,
            intent=intent,
            query=query,
        )
        attempts.append({"backend": "azure_openai", **azure_meta})
        if polished:
            return polished, {
                "lane": "research_only",
                "hypothesis_tier": "B",
                "backend": "azure_openai",
                "applied": True,
                "attempts": attempts,
                **{k: v for k, v in azure_meta.items() if k not in {"backend", "applied"}},
            }

    return None, {
        "lane": "research_only",
        "hypothesis_tier": "B",
        "backend": "none",
        "applied": False,
        "reason": attempts[-1].get("reason") if attempts else "no_backend_enabled",
        "attempts": attempts,
    }


def ollama_polish_summary(
    summary_ko: str,
    *,
    intent: str,
    query: str,
    timeout_sec: int = DEFAULT_TIMEOUT,
    force: bool = False,
) -> tuple[str | None, dict[str, Any]]:
    meta: dict[str, Any] = {
        "lane": "research_only",
        "hypothesis_tier": "B",
        "backend": "ollama",
        "model": _model(),
        "applied": False,
    }
    if not summary_ko.strip():
        meta["reason"] = "empty_summary"
        return None, meta
    if not force and not polish_enabled():
        meta["reason"] = "disabled"
        return None, meta

    host = _host()
    model = _model()
    prompt = build_polish_user_prompt(summary_ko=summary_ko, intent=intent, query=query)
    body = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.35, "num_predict": 120},
    }
    try:
        req = urllib.request.Request(
            f"{host}/api/generate",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            gen = json.loads(resp.read().decode("utf-8"))
        polished = _clean_polished(str(gen.get("response") or ""))
        if len(polished) < 8:
            meta["reason"] = "empty_response"
            return None, meta
        meta["applied"] = True
        meta["host"] = host
        meta["polished_at_utc"] = _utc_now()
        return polished, meta
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        meta["reason"] = str(exc)[:200]
        return None, meta


def enrich_package_with_preset_polish(
    package: dict[str, Any],
    *,
    force: bool = False,
    timeout_sec: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Attach moment_preset_polish_v1 for canonical preset queries + hero line."""
    import assemble_personadiary_moment_response_v1 as asm  # noqa: WPS433

    presets_out: dict[str, Any] = {}
    for intent, query in PRESET_QUERIES.items():
        moment = asm.assemble_moment_response(package, query)
        summary = str(moment.get("summary_ko") or "")
        polished, meta = polish_summary_with_fallback(
            summary,
            intent=intent,
            query=query,
            timeout_sec=timeout_sec,
            force=force,
            mode="batch",
        )
        presets_out[intent] = {
            "canonical_query": query,
            "summary_ko_deterministic": summary,
            "summary_ko_polished": polished,
            "polish_meta": meta,
        }

    hero = next((b for b in package.get("ui_blocks") or [] if b.get("type") == "hero"), None)
    hero_body = str((hero or {}).get("body_ko") or "")
    hero_polished, hero_meta = polish_summary_with_fallback(
        hero_body,
        intent="reflect",
        query="오늘의 마음 가이드",
        timeout_sec=timeout_sec,
        force=force,
        mode="batch",
    )

    package["moment_preset_polish_v1"] = {
        "schema": "personadiary_moment_preset_polish_v1",
        "hypothesis_tier": "B",
        "lane": "research_only",
        "preview_only": True,
        "generated_at_utc": _utc_now(),
        "presets": presets_out,
        "hero": {
            "body_ko_deterministic": hero_body,
            "body_ko_polished": hero_polished,
            "polish_meta": hero_meta,
        },
        "explicit_gaps": [
            "Polish is [HYPO] — deterministic summary remains SSOT for gates.",
            "Applied only for canonical preset queries on exact match in API.",
            "Runtime API: Azure direct polish; Ollama generate not used on live path.",
            "Batch preset polish: optional Ollama then Azure (MKM_PERSONADIARY_MOMENT_OLLAMA_POLISH=1).",
            "No Track A / mkmlife payment / live trading merge.",
        ],
    }
    return package
