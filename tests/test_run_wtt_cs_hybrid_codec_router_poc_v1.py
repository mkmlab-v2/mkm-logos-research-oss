"""run_wtt_cs_hybrid_codec_router_poc_v1 — routing heuristics (no API)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.compression_hybrid_codec_router_v1_lib import (
    has_assistant_turn,
    select_profile_assistant_literal,
    select_profile_turns_gte,
    turn_count,
)


def test_turn_count_and_route_gte_3() -> None:
    multi = {
        "turns": [
            {"role": "user", "text": "a"},
            {"role": "assistant", "text": "b"},
            {"role": "user", "text": "c"},
        ]
    }
    short = {"turns": [{"role": "user", "text": "a"}, {"role": "user", "text": "b"}]}
    assert turn_count(multi["turns"]) == 3
    assert turn_count(short["turns"]) == 2
    assert select_profile_turns_gte(multi["turns"], min_turns=3) == ("literal", "turn_count>=3")
    assert select_profile_turns_gte(short["turns"], min_turns=3) == ("economy", "economy_default")


def test_assistant_route() -> None:
    with_asst = {
        "turns": [
            {"role": "user", "text": "a"},
            {"role": "assistant", "text": "b"},
        ]
    }
    user_only = {"turns": [{"role": "user", "text": "a"}, {"role": "user", "text": "b"}]}
    assert has_assistant_turn(with_asst["turns"]) is True
    assert has_assistant_turn(user_only["turns"]) is False
    assert select_profile_assistant_literal(with_asst["turns"]) == ("literal", "has_assistant_turn")
    assert select_profile_assistant_literal(user_only["turns"]) == ("economy", "economy_default")
