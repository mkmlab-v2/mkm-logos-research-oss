"""BigSet LLM profile helpers — OpenRouter :free · Ollama · Azure OpenAI (B-track).

No secrets logged. SSOT for model routing env consumed by `bigset start` backend.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

# BigSet backend reads these at process start (see ~/.bigset/.../backend.mjs).
FREE_TIER_ENV_KEYS = (
    "SCHEMA_INFERENCE_MODEL",
    "POPULATE_ORCHESTRATOR_MODEL",
    "INVESTIGATE_SUBAGENT_MODEL",
    "OPENROUTER_BASE_URL",
)

DEFAULT_FREE_MODEL = "openrouter/free"
DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"


def load_dotenv_quiet() -> None:
    if not ENV_PATH.is_file():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _azure_openai_base_url() -> str | None:
    endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
    if not endpoint:
        return None
    return f"{endpoint}/openai/v1"


def resolve_profile(*, mode: str | None = None) -> dict[str, str]:
    """Return non-secret BigSet model routing profile from env."""
    load_dotenv_quiet()
    profile_mode = (mode or os.environ.get("BIGSET_LLM_PROFILE") or "openrouter_free").strip().lower()
    if profile_mode in {"azure", "azure_openai", "azure_first"}:
        deployment = (
            os.environ.get("BIGSET_AZURE_DEPLOYMENT")
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            or "gpt-4o-mini"
        ).strip()
        base = _azure_openai_base_url() or ""
        return {
            "profile_mode": "azure_openai",
            "SCHEMA_INFERENCE_MODEL": deployment,
            "POPULATE_ORCHESTRATOR_MODEL": deployment,
            "INVESTIGATE_SUBAGENT_MODEL": deployment,
            "OPENROUTER_BASE_URL": base,
        }
    if profile_mode in {"ollama", "local", "ollama_local"}:
        model = (os.environ.get("BIGSET_OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip()
        base = (os.environ.get("BIGSET_OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_BASE).strip()
        if not base.endswith("/v1"):
            base = base.rstrip("/") + "/v1"
        return {
            "profile_mode": "ollama_local",
            "SCHEMA_INFERENCE_MODEL": model,
            "POPULATE_ORCHESTRATOR_MODEL": model,
            "INVESTIGATE_SUBAGENT_MODEL": model,
            "OPENROUTER_BASE_URL": base,
            "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY") or "ollama",
        }
    model = (
        os.environ.get("BIGSET_FREE_SCHEMA_MODEL")
        or os.environ.get("BIGSET_FREE_MODEL")
        or DEFAULT_FREE_MODEL
    ).strip()
    populate = (os.environ.get("BIGSET_FREE_POPULATE_MODEL") or model).strip()
    investigate = (os.environ.get("BIGSET_FREE_INVESTIGATE_MODEL") or model).strip()
    return {
        "profile_mode": "openrouter_free",
        "SCHEMA_INFERENCE_MODEL": model,
        "POPULATE_ORCHESTRATOR_MODEL": populate,
        "INVESTIGATE_SUBAGENT_MODEL": investigate,
        "OPENROUTER_BASE_URL": (os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").strip(),
    }


def apply_profile_to_environ(profile: dict[str, str]) -> dict[str, str]:
    """Apply profile keys to os.environ; return applied map (no API key values)."""
    applied: dict[str, str] = {}
    for key in FREE_TIER_ENV_KEYS:
        if key in profile and profile[key]:
            os.environ[key] = profile[key]
            applied[key] = profile[key]
    if profile.get("profile_mode") == "ollama_local":
        os.environ.setdefault("OPENROUTER_API_KEY", "ollama")
    elif profile.get("profile_mode") == "azure_openai":
        azure_key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
        if azure_key:
            os.environ["OPENROUTER_API_KEY"] = azure_key
    elif profile.get("profile_mode") == "openrouter_free":
        key = (os.environ.get("OPENROUTER_API_KEY") or "").strip()
        if not key:
            try:
                from scripts.configure_bigset_local_credentials_v1 import _load_dotenv_quiet, _resolve_secret

                _load_dotenv_quiet()
                key = (_resolve_secret("OPENROUTER_API_KEY") or "").strip()
            except Exception:
                key = ""
        if key:
            os.environ["OPENROUTER_API_KEY"] = key
    return applied


def profile_public_snapshot(profile: dict[str, str]) -> dict[str, Any]:
    mode = profile.get("profile_mode")
    if mode == "azure_openai":
        cost_tier = "azure_credit"
        rate_note = "Azure startup credits; MKM_LLM_PRIORITY=azure_first — personal card $0 when credits cover usage"
    elif mode == "ollama_local":
        cost_tier = "tier_0"
        rate_note = "Local Ollama; schema inference quality model-dependent (prefer athena-merged-v2 over gemma4:e2b)"
    else:
        cost_tier = "tier_0"
        rate_note = "OpenRouter :free ≈ 20 rpm / 50 rpd (account-dependent); quality not guaranteed"
    return {
        "profile_mode": mode,
        "SCHEMA_INFERENCE_MODEL": profile.get("SCHEMA_INFERENCE_MODEL"),
        "POPULATE_ORCHESTRATOR_MODEL": profile.get("POPULATE_ORCHESTRATOR_MODEL"),
        "INVESTIGATE_SUBAGENT_MODEL": profile.get("INVESTIGATE_SUBAGENT_MODEL"),
        "OPENROUTER_BASE_URL": profile.get("OPENROUTER_BASE_URL"),
        "cost_tier": cost_tier,
        "rate_limit_note": rate_note,
    }


def azure_credentials_present() -> bool:
    load_dotenv_quiet()
    return bool(
        (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip()
        and (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
        and (
            (os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "").strip()
            or (os.environ.get("BIGSET_AZURE_DEPLOYMENT") or "").strip()
        )
    )
