"""Resolve Cloudflare API token — match PowerShell scripts (User before Process before .env)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Zone SSOT — jema-ai.com dynamic redirect (smartfarm, studio bridge, apex rules)
JEMA_AI_ZONE_ID = "e64f17593ce48e31c2839b421c8bd4c0"

# Dedicated first; then rulesets keys (must include jema-ai.com + Zone Rulesets Edit, not jemaai.cloud-only).
JEMA_AI_REDIRECT_TOKEN_KEYS: tuple[str, ...] = (
    "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN",
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "MKM_CLOUDFLARE_RULESETS_TOKEN",
)


def _read_dotenv_key(key: str) -> str:
    env = ROOT / ".env"
    if not env.is_file():
        return ""
    prefix = f"{key}="
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _read_dotenv_token() -> tuple[str, str]:
    for key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN"):
        v = _read_dotenv_key(key)
        if v:
            return v, f".env:{key}"
    return "", ""


def _read_windows_user_env(key: str) -> str:
    if sys.platform != "win32":
        return ""
    ps = (
        f"[Environment]::GetEnvironmentVariable('{key}', 'User')"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return (out.stdout or "").strip()
    except (subprocess.TimeoutExpired, OSError):
        return ""


def resolve_cloudflare_token(*, extra_keys: tuple[str, ...] = ()) -> tuple[str, str]:
    """
    Order: dedicated extra_keys (User) -> CLOUDFLARE_API_TOKEN/CF_API_TOKEN User ->
    Machine -> Process -> .env
    """
    for key in extra_keys:
        v = _read_windows_user_env(key)
        if v:
            return v, f"user_env:{key}"
        v = os.environ.get(key, "").strip()
        if v:
            return v, f"process_env:{key}"
        v = _read_dotenv_key(key)
        if v:
            return v, f".env:{key}"
    for key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN"):
        v = _read_windows_user_env(key)
        if v:
            return v, f"user_env:{key}"
        v = os.environ.get(key, "").strip()
        if v:
            return v, f"process_env:{key}"
    v, src = _read_dotenv_token()
    if v:
        return v, src
    return "", "none"


def token_fingerprint(token: str) -> str:
    t = token.strip()
    if len(t) < 12:
        return "(short)"
    return f"{t[:6]}...{t[-4:]}"


def resolve_cloudflare_jema_ai_redirect_token() -> tuple[str, str]:
    """Token for jema-ai.com http_request_dynamic_redirect (NOT general DNS token)."""
    return resolve_cloudflare_token(extra_keys=JEMA_AI_REDIRECT_TOKEN_KEYS)
