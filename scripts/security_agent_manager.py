#!/usr/bin/env python3
"""Local Security Agent PoC: resolve secrets from Windows DPAPI store only.

Does not implement compression-as-encryption. Keys never pass through LLM context;
this module only bridges ``Invoke-EncryptedSecretStore.ps1`` for subprocess-local use.

Disable with env ``MKM_SKIP_DPAPI_SECRET_STORE=1`` (truthy).
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PS1 = _REPO_ROOT / "scripts" / "Invoke-EncryptedSecretStore.ps1"


def _truthy_skip_dpapi() -> bool:
    raw = (os.environ.get("MKM_SKIP_DPAPI_SECRET_STORE") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _get_plain_from_dpapi_store(key: str) -> Optional[str]:
    """Return plaintext for *key* from DPAPI JSON store, or None if unavailable."""
    if _truthy_skip_dpapi():
        return None
    if os.name != "nt":
        return None
    if not key or not key.strip():
        return None
    if not _PS1.is_file():
        logger.debug("DPAPI helper missing: %s", _PS1)
        return None

    key_clean = key.strip()
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(_PS1),
        "-Action",
        "get",
        "-Key",
        key_clean,
        "-AsPlainText",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.debug("DPAPI store subprocess failed: %s", e)
        return None

    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        if err:
            logger.debug("DPAPI get stderr (%s): %s", key_clean, err[:500])
        return None

    out = (proc.stdout or "").strip()
    return out if out else None


class SecurityAgent:
    """Broker façade: maps env-style names to DPAPI-backed entries (same key names)."""

    def get_env_var(self, name: str) -> Optional[str]:
        return _get_plain_from_dpapi_store(name)


_agent: Optional[SecurityAgent] = None


def get_security_agent() -> SecurityAgent:
    global _agent
    if _agent is None:
        _agent = SecurityAgent()
    return _agent
