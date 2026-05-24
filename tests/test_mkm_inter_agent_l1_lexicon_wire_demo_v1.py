"""mkm_lexicon_wire_v1 adaptive msgpack roundtrip."""

from __future__ import annotations

import pytest

msgpack = pytest.importorskip("msgpack")

from scripts.l1_side_channel_wire_codec import decode_adaptive_msgpack, encode_adaptive_msgpack


def test_lexicon_wire_payload_roundtrip() -> None:
    payload = {
        "schema": "mkm_lexicon_wire_v1",
        "symbol_key": "atom_id",
        "atom_id_sequence": ["other::strong", "greek::και"],
    }
    wire, variant = encode_adaptive_msgpack(payload)
    out = decode_adaptive_msgpack(wire)
    assert out["atom_id_sequence"] == payload["atom_id_sequence"]
    assert variant in ("raw", "zstd")
