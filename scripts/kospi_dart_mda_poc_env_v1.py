#!/usr/bin/env python3
"""Load workspace .env for KOSPI DART PoC scripts (no secret logging)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def load_workspace_dotenv() -> bool:
    if not ENV_PATH.is_file():
        return False
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv(ENV_PATH, override=False)
    return True


def dart_api_key() -> str:
    load_workspace_dotenv()
    return str(os.environ.get("DART_API_KEY", "")).strip()
