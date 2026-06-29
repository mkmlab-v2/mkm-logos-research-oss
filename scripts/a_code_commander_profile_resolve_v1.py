#!/usr/bin/env python3
"""Resolve commander profile path: local > env > example ([HYPO] / RQ-028)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PROFILE = ROOT / "data" / "personalization" / "commander_profile_v1.local.json"
EXAMPLE_PROFILE = ROOT / "docs" / "final" / "artifacts" / "commander_profile_v1.example.json"

ProfileSource = Literal["explicit", "local", "env", "example"]


def resolve_commander_profile_path(explicit: Path | None = None) -> tuple[Path, ProfileSource]:
    if explicit is not None:
        p = explicit.expanduser()
        if p.is_file():
            return p.resolve(), "explicit"
        raise FileNotFoundError(f"commander profile not found: {p}")

    env_raw = os.getenv("MKM_COMMANDER_PROFILE_JSON", "").strip()
    if env_raw:
        env_path = Path(env_raw)
        if not env_path.is_absolute():
            env_path = ROOT / env_path
        if env_path.is_file():
            return env_path.resolve(), "env"

    if LOCAL_PROFILE.is_file():
        return LOCAL_PROFILE.resolve(), "local"

    if not EXAMPLE_PROFILE.is_file():
        raise FileNotFoundError(f"commander profile example missing: {EXAMPLE_PROFILE}")
    return EXAMPLE_PROFILE.resolve(), "example"
