"""Round-trip tests for L1 side-channel wire codec (optional deps)."""

from __future__ import annotations

import pytest

msgpack = pytest.importorskip("msgpack")
zstandard = pytest.importorskip("zstandard")

from scripts.l1_side_channel_wire_codec import (
    decode_adaptive_msgpack,
    decode_msgpack,
    decode_msgpack_zstd,
    encode_adaptive_msgpack,
    encode_msgpack_zstd,
    merge_side_channel,
    minimal_payload,
    msgpack_payload_bytes,
)
from scripts.run_l1_permutation_channel_integrated_spike import (
    noisify_with_side_channel,
    restore_from_side_channel,
)


def test_msgpack_zstd_round_trip_restores_source() -> None:
    import random

    rng = random.Random(42)
    src = "BTC 50000 hit Q1 2026"
    noisy, _mode, sc = noisify_with_side_channel(src, rng, 0.2, forced_mode="swap_typo")
    payload = minimal_payload(sc)
    zblob = encode_msgpack_zstd(payload, level=3)
    assert zblob is not None
    decoded = decode_msgpack_zstd(zblob)
    merged = merge_side_channel(sc["mode"], decoded)
    assert restore_from_side_channel(noisy, merged) == src


def test_msgpack_alone_round_trip() -> None:
    payload = {
        "swap_log": [[0, 1]],
        "typo_patches": [],
        "oov_stack": [],
    }
    b = msgpack_payload_bytes(payload)
    assert b is not None
    out = decode_msgpack(b)
    assert out == payload


def test_adaptive_wire_round_trip() -> None:
    payload = {
        "swap_log": [[0, 1]],
        "typo_patches": [],
        "oov_stack": [],
    }
    wire, _variant = encode_adaptive_msgpack(payload, zstd_min_raw_bytes=64, zstd_level=3)
    assert decode_adaptive_msgpack(wire) == payload
