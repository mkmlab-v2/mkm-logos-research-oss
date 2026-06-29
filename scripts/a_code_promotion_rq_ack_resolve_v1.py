#!/usr/bin/env python3
"""Resolve commander A-code promotion RQ ack path ([HYPO] / RQ-031)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ACK = ROOT / "data/personalization/commander_a_code_promotion_rq_ack_v1.local.json"
EXAMPLE_ACK = ROOT / "data/personalization/commander_a_code_promotion_rq_ack_v1.local.json.example"

AckSource = Literal["explicit", "local", "env", "example", "absent"]


def resolve_promotion_rq_ack_path(
    explicit: Path | None = None,
    *,
    allow_example: bool = False,
) -> tuple[Path | None, AckSource]:
    if explicit is not None:
        p = explicit.expanduser()
        if p.is_file():
            return p.resolve(), "explicit"
        raise FileNotFoundError(f"promotion rq ack not found: {p}")

    env_raw = os.getenv("MKM_COMMANDER_A_CODE_PROMOTION_RQ_ACK_JSON", "").strip()
    if env_raw:
        env_path = Path(env_raw)
        if not env_path.is_absolute():
            env_path = ROOT / env_path
        if env_path.is_file():
            return env_path.resolve(), "env"

    if LOCAL_ACK.is_file():
        return LOCAL_ACK.resolve(), "local"

    if allow_example and EXAMPLE_ACK.is_file():
        return EXAMPLE_ACK.resolve(), "example"

    return None, "absent"
