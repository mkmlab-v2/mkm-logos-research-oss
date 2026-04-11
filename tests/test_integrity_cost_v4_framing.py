# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.6, L:0.5, K:0.6, M:0.4}
# Balance: 85
# Purpose: v4 MergedSeg → delta_bundle_v1 framing mapping smoke test.
# Keywords: integrity, framing, codec
from __future__ import annotations

from scripts.calculate_integrity_cost_v4 import (
    MergedSeg,
    framing_bytes_delta_bundle_v1,
    framing_bytes_varint4,
    merged_segments_to_delta_bundle_pairs,
)
from scripts.core.codec_v1 import decode_delta_bundle_v1, encode_delta_bundle_v1


def test_merged_to_bundle_roundtrip_tags() -> None:
    merged = [MergedSeg(i1=2, i2=5, j1=1, j2=4)]
    o, p = merged_segments_to_delta_bundle_pairs(merged)
    assert o == [2, 1, 3, 3]
    assert p == [0, 1, 2, 3]
    blob = encode_delta_bundle_v1(o, p)
    o2, p2 = decode_delta_bundle_v1(blob)
    assert list(o2) == o
    assert list(p2) == p


def test_framing_bundle_nonnegative() -> None:
    merged = [
        MergedSeg(0, 1, 0, 2),
        MergedSeg(10, 12, 8, 9),
    ]
    fb = framing_bytes_delta_bundle_v1(merged)
    fv = sum(framing_bytes_varint4(m.i1, m.j1, m.i2 - m.i1, m.j2 - m.j1) for m in merged)
    assert fb > 0 and fv > 0
