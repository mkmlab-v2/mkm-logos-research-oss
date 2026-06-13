"""Resume pack repair_v2 slice mode ([HYPO] / research_only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_mkm_chat_resume_pack_v1 import (  # noqa: E402
    _load_ops_pins,
    _synthetic_repair_query,
)


def test_synthetic_repair_query_prefers_topic() -> None:
    routed = [
        (
            "n1",
            {
                "essence": "web_ops gate",
                "must_keep_tags": ["research_only"],
            },
        )
    ]
    q = _synthetic_repair_query(routed, topic="Nebius cost audit")
    assert "Nebius cost audit" in q
    assert "web_ops gate" in q
    assert "research_only" in q


def test_load_ops_pins_repair_v2_mode() -> None:
    if not (ROOT / "storage/meta/mkm_ops_memory_index_v1.json").is_file():
        pytest.skip("ops memory index missing")
    pins, repair_text = _load_ops_pins(
        ROOT,
        top_n=2,
        lane=None,
        commander_default=False,
        include_slice=False,
        repair_v2_slice=True,
        slice_max_chars=400,
        topic="ops memory inject",
    )
    if not pins:
        pytest.skip("no routed pins")
    assert repair_text is not None
    assert all(pin.get("slice_mode") == "repair_v2" for pin in pins)
    assert "slice_preview" not in pins[0]
