from __future__ import annotations

import json
from pathlib import Path

from scripts.core.contextual_generator_v5_codec import ContextualGeneratorV5Codec


def test_contextual_generator_v5_codec_roundtrip_has_slots() -> None:
    gen = ContextualGeneratorV5Codec()
    encoded = gen.encode(
        raw="state policy boundary evidence manual 체질 성경 alignment",
        state16=11,
        must_keep={"명리"},
    )
    assert "ST11" in encoded
    decoded = gen.decode(encoded=encoded, raw="state policy boundary evidence manual 체질 성경 alignment")
    assert isinstance(decoded, str)
    assert len(decoded) > 0
    assert "state" in decoded.lower()


def test_contextual_generator_v5_codec_loads_slot_dictionary(tmp_path: Path) -> None:
    slot_file = tmp_path / "slot.json"
    slot_file.write_text(
        json.dumps({"slots": {"S1": ["custom_state"], "S2": [], "S3": [], "S4": [], "S5": [], "S6": [], "S7": []}}),
        encoding="utf-8",
    )
    gen = ContextualGeneratorV5Codec(slot_dict_path=slot_file)
    encoded = gen.encode(raw="custom_state marker", state16=1, must_keep=set())
    assert "S1" in encoded


def test_contextual_generator_v5_hybrid_decode_respects_budget() -> None:
    gen = ContextualGeneratorV5Codec()
    raw = "state policy trigger boundary evidence manual strict review sasang 체질 성경 logos alignment cadence"
    encoded = gen.encode(raw=raw, state16=2, must_keep=set())
    dec = gen.decode_hybrid(encoded=encoded, raw=raw, max_tokens_ratio=0.5)
    assert len(dec.split()) <= int(len(raw.split()) * 0.5)
