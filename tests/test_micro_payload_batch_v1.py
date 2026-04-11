# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.6, K:0.5, M:0.5}
# Balance: 86
# Purpose: Round-trip and error paths for micro_payload_batch_v1.
# Keywords: batch, capsule, test
from __future__ import annotations

from scripts.core.micro_payload_batch_v1 import (
    SIGNATURE_RESERVED_BYTES,
    BatchCapsuleError,
    decode_batch_v1,
    encode_batch_v1,
    overhead_bytes_v1,
)


def test_roundtrip_empty_and_multiple() -> None:
    for payloads in [[], [b"a"], [b"foo", b"bar", "\uac00".encode("utf-8")]]:
        raw = encode_batch_v1(list(payloads))
        cap = decode_batch_v1(raw)
        assert list(cap.payloads) == payloads
        assert len(cap.signature_reserved) == SIGNATURE_RESERVED_BYTES
        assert cap.signature_reserved == bytes(SIGNATURE_RESERVED_BYTES)


def test_custom_signature_placeholder() -> None:
    sig = bytes(range(48))
    raw = encode_batch_v1([b"x"], signature_placeholder=sig)
    cap = decode_batch_v1(raw)
    assert cap.signature_reserved == sig


def test_bad_magic() -> None:
    raw = encode_batch_v1([b"a"])
    corrupted = b"XXXX" + raw[4:]
    try:
        decode_batch_v1(corrupted)
    except BatchCapsuleError:
        return
    raise AssertionError("expected BatchCapsuleError")


def test_overhead_formula() -> None:
    assert overhead_bytes_v1(0) == 4 + 2 + 4 + 0 + 48
    assert overhead_bytes_v1(3) == 4 + 2 + 4 + 12 + 48
