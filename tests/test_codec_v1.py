# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.6, K:0.5, M:0.5}
# Balance: 86
# Purpose: codec_v1 round-trip, kill-zone (≤15 B), rANS spike, u32 savings.
# Keywords: codec, test, varint, rANS
from __future__ import annotations

import random

import pytest

from scripts.core.codec_v1 import (
    KILL_ZONE_MAX_PAIRS,
    CodecV1Error,
    baseline_fixed_u32_pairs_bytes,
    decode_delta_bundle_v1,
    decode_opcodes_rans_spike,
    encode_delta_bundle_v1,
    encode_opcodes_rans_spike,
    marginal_metadata_bytes_v1,
    savings_vs_u32_baseline,
    shannon_bits_lower_bound,
)


def test_delta_bundle_roundtrip_various() -> None:
    cases = [
        ([], []),
        ([0], [0]),
        ([-1, 2, -3], [0, 1, 2]),
        ([10**9], [3]),
    ]
    for offs, ops in cases:
        raw = encode_delta_bundle_v1(offs, ops)
        o2, p2 = decode_delta_bundle_v1(raw)
        assert list(o2) == offs
        assert list(p2) == ops


def test_kill_zone_fifteen_bytes_or_less() -> None:
    """Gap-1 style: small signed limbs, tiny opcode alphabet — bounded marginal bundle ≤15 B."""
    rng = random.Random(42)
    for n in range(0, KILL_ZONE_MAX_PAIRS + 1):
        for _ in range(200):
            offs = [rng.randint(-63, 63) for _ in range(n)]
            ops = [rng.randint(0, 3) for _ in range(n)]
            b = marginal_metadata_bytes_v1(offs, ops)
            assert b <= 15, (n, offs, ops, b)


def test_kill_zone_n10_can_exceed_fifteen() -> None:
    """Structural worst case: 1-byte zigzag + 2-bit opcode alphabet → n=10 hits 16 bytes."""
    offs = [0] * 10
    ops = [3] * 10
    assert marginal_metadata_bytes_v1(offs, ops) == 16


def test_savings_vs_naive_u32() -> None:
    offs = [0, 1, -2, 3]
    ops = [0, 1, 2, 3]
    assert baseline_fixed_u32_pairs_bytes(4) == 32
    assert savings_vs_u32_baseline(offs, ops) == 32 - marginal_metadata_bytes_v1(offs, ops)
    assert savings_vs_u32_baseline(offs, ops) > 0


def test_rans_spike_roundtrip_skewed() -> None:
    syms = [0, 0, 0, 0, 1, 2, 0, 3, 0, 0]
    blob = encode_opcodes_rans_spike(syms)
    out = decode_opcodes_rans_spike(blob, len(syms))
    assert out == tuple(syms)


def test_shannon_vs_rans_blob_length() -> None:
    freqs = (230, 10, 8, 8)
    syms = [0] * 20 + [1] * 2
    bits = shannon_bits_lower_bound(freqs, syms)
    blob = encode_opcodes_rans_spike(syms, freqs=freqs)
    assert len(blob) * 8 <= bits + 64


def test_trailing_bytes_rejected() -> None:
    raw = encode_delta_bundle_v1([1], [0]) + b"\xff"
    with pytest.raises(CodecV1Error):
        decode_delta_bundle_v1(raw)
