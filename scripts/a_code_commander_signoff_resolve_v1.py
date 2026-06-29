#!/usr/bin/env python3
"""Resolve commander A-code sign-off path: local > env > absent ([HYPO] / RQ-029)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
LOCAL_SIGNOFF = ROOT / "data" / "personalization" / "commander_a_code_signoff_v1.local.json"
EXAMPLE_SIGNOFF = ROOT / "data" / "personalization" / "commander_a_code_signoff_v1.local.json.example"

SignoffSource = Literal["explicit", "local", "env", "example", "absent"]


def resolve_commander_a_code_signoff_path(
    explicit: Path | None = None,
    *,
    allow_example: bool = False,
) -> tuple[Path | None, SignoffSource]:
    if explicit is not None:
        p = explicit.expanduser()
        if p.is_file():
            return p.resolve(), "explicit"
        raise FileNotFoundError(f"commander a-code signoff not found: {p}")

    env_raw = os.getenv("MKM_COMMANDER_A_CODE_SIGNOFF_JSON", "").strip()
    if env_raw:
        env_path = Path(env_raw)
        if not env_path.is_absolute():
            env_path = ROOT / env_path
        if env_path.is_file():
            return env_path.resolve(), "env"

    if LOCAL_SIGNOFF.is_file():
        return LOCAL_SIGNOFF.resolve(), "local"

    if allow_example and EXAMPLE_SIGNOFF.is_file():
        return EXAMPLE_SIGNOFF.resolve(), "example"

    return None, "absent"
