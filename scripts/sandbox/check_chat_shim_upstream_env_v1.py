#!/usr/bin/env python3
"""Check MKM_CHAT_SHIM upstream env presence without printing secrets."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"

PROVIDER_ENV = "MKM_CHAT_SHIM_UPSTREAM_PROVIDER"

FALLBACK_KEY_ENV = (
    "MKM_CHAT_SHIM_UPSTREAM_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "NEBIUS_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)

OPENROUTER_OPENAI_BASE = "https://openrouter.ai/api/v1"
OLLAMA_OPENAI_BASE = "http://127.0.0.1:11434/v1"
NEBIUS_OPENAI_BASE = "https://api.studio.nebius.ai/v1"
DEFAULT_NEBIUS_MODEL = "meta-llama/Meta-Llama-3.1-70B-Instruct"

GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"


def _read_env_file() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return out
    for line in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        name, val = s.split("=", 1)
        out[name.strip()] = val.strip().strip('"').strip("'")
    return out


def _get_var(name: str, file_env: dict[str, str], *, prefer_file: bool) -> str:
    if prefer_file:
        return file_env.get(name, "").strip() or os.environ.get(name, "").strip()
    return os.environ.get(name, "").strip() or file_env.get(name, "").strip()


def _provider_order(provider: str) -> tuple[str, ...]:
    p = (provider or "auto").strip().lower()
    if p == "openrouter":
        return ("OPENROUTER_API_KEY", "MKM_CHAT_SHIM_UPSTREAM_API_KEY")
    if p == "deepseek":
        return ("DEEPSEEK_API_KEY", "MKM_CHAT_SHIM_UPSTREAM_API_KEY")
    if p == "gemini":
        return ("GEMINI_API_KEY", "GOOGLE_API_KEY", "MKM_CHAT_SHIM_UPSTREAM_API_KEY")
    if p == "ollama":
        return ("MKM_CHAT_SHIM_UPSTREAM_API_KEY",)
    if p == "openai":
        return ("OPENAI_API_KEY", "MKM_CHAT_SHIM_UPSTREAM_API_KEY")
    return FALLBACK_KEY_ENV


def _pick_api_key(
    file_env: dict[str, str], *, prefer_file: bool, provider: str
) -> tuple[str, str | None]:
    names = _provider_order(provider)
    if prefer_file:
        for name in names:
            val = file_env.get(name, "").strip()
            if val:
                return val, name
    for name in names:
        val = os.environ.get(name, "").strip() or file_env.get(name, "").strip()
        if val:
            return val, name
    if provider == "ollama":
        return "ollama", "ollama_local"
    return "", None


def _infer_base_and_model(
    *,
    key_source: str | None,
    base: str,
    model: str,
    provider: str,
    file_env: dict[str, str],
) -> tuple[str, str]:
    if base:
        return base, model
    p = (provider or "auto").strip().lower()
    if p == "ollama" or key_source == "ollama_local":
        m = (
            model
            if model and model != "gpt-4.1-mini"
            else _get_var("OLLAMA_MODEL", file_env, prefer_file=True) or DEFAULT_OLLAMA_MODEL
        )
        return OLLAMA_OPENAI_BASE, m
    if key_source == "OPENROUTER_API_KEY" or p == "openrouter":
        m = (
            model
            if model and model != "gpt-4.1-mini"
            else _get_var("OPENROUTER_MODEL", file_env, prefer_file=True)
            or "google/gemini-2.0-flash-exp:free"
        )
        return OPENROUTER_OPENAI_BASE, m
    if key_source == "DEEPSEEK_API_KEY":
        m = model if model != "gpt-4.1-mini" else "deepseek-chat"
        return "https://api.deepseek.com", m
    if key_source == "NEBIUS_API_KEY":
        m = model if model and model != "gpt-4.1-mini" else DEFAULT_NEBIUS_MODEL
        return NEBIUS_OPENAI_BASE, m
    if key_source in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}:
        m = model if model and model != "gpt-4.1-mini" else DEFAULT_GEMINI_MODEL
        return GEMINI_OPENAI_BASE, m
    if key_source in {
        "OPENAI_API_KEY",
        "MKM_CHAT_SHIM_UPSTREAM_API_KEY",
    }:
        return "https://api.openai.com", model
    return base, model


def _resolve(*, prefer_file: bool, apply: bool) -> dict[str, object]:
    file_env = _read_env_file()
    provider = _get_var(PROVIDER_ENV, file_env, prefer_file=prefer_file) or "auto"
    base = _get_var("MKM_CHAT_SHIM_UPSTREAM_BASE_URL", file_env, prefer_file=prefer_file)
    model = _get_var("MKM_CHAT_SHIM_UPSTREAM_MODEL", file_env, prefer_file=prefer_file) or "gpt-4.1-mini"
    key, key_source = _pick_api_key(file_env, prefer_file=prefer_file, provider=provider)
    base, model = _infer_base_and_model(
        key_source=key_source,
        base=base,
        model=model,
        provider=provider,
        file_env=file_env,
    )
    if base and "openai.com" in base and key_source in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}:
        base, model = _infer_base_and_model(
            key_source=key_source,
            base="",
            model=model,
            provider=provider,
            file_env=file_env,
        )

    if apply:
        if base:
            os.environ["MKM_CHAT_SHIM_UPSTREAM_BASE_URL"] = base
        if key:
            os.environ["MKM_CHAT_SHIM_UPSTREAM_API_KEY"] = key
        os.environ["MKM_CHAT_SHIM_UPSTREAM_MODEL"] = model
        if provider:
            os.environ[PROVIDER_ENV] = provider

    return {
        "base_url_set": bool(base),
        "api_key_set": bool(key),
        "model": model,
        "configured": bool(base and key),
        "base_url_hint": base.split("/")[2] if base and "://" in base else None,
        "key_source": key_source,
        "upstream_provider": provider or "auto",
        "prefer_file_env": prefer_file,
    }


def resolve_upstream_config() -> dict[str, object]:
    return _resolve(prefer_file=True, apply=False)


def apply_upstream_env() -> dict[str, object]:
    """Load workspace .env into os.environ for shim upstream (no secret values returned)."""
    return _resolve(prefer_file=True, apply=True)


if __name__ == "__main__":
    import json

    print(json.dumps(resolve_upstream_config(), ensure_ascii=False))
