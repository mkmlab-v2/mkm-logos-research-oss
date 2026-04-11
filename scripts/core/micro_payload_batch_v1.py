# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.75, L:0.5, K:0.85, M:0.45}
# Balance: 88
# Purpose: N-payload batch capsule wire format with reserved 48B signature slot (BLS placeholder).
# Keywords: batch, capsule, micro-payload, framing, BEP
"""Micro-payload batch capsule v1 — binary framing for amortized security / network layers.

Wire layout (big-endian):
  magic[4]      = b"MKM1"
  version[2]    = uint16 (1)
  count[4]      = uint32 = number of payloads
  repeat count:
    len[4]      = uint32 payload byte length
    payload     = len bytes
  sig_reserved[48] = placeholder for aggregated signature (e.g. BLS); zeros in spike.

Not a TLS/gRPC replacement; blueprint for BatchEncoder integration and BEP (N_BEP) tests.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIC = b"MKM1"
VERSION_V1 = 1
SIGNATURE_RESERVED_BYTES = 48
_HEADER_NO_SIG = 4 + 2 + 4  # magic + version + count


@dataclass(frozen=True)
class BatchCapsuleV1:
    """Decoded batch: ordered payloads + 48-byte signature slot (opaque)."""

    version: int
    payloads: tuple[bytes, ...]
    signature_reserved: bytes

    def __post_init__(self) -> None:
        if len(self.signature_reserved) != SIGNATURE_RESERVED_BYTES:
            raise ValueError("signature_reserved must be 48 bytes")


class BatchCapsuleError(ValueError):
    """Invalid capsule bytes."""


def encode_batch_v1(payloads: list[bytes], *, signature_placeholder: bytes | None = None) -> bytes:
    """Pack UTF-8 or arbitrary bytes payloads; trailing 48B sig slot (zeros by default)."""
    if signature_placeholder is None:
        sig = bytes(SIGNATURE_RESERVED_BYTES)
    else:
        if len(signature_placeholder) != SIGNATURE_RESERVED_BYTES:
            raise ValueError(f"signature_placeholder must be {SIGNATURE_RESERVED_BYTES} bytes")
        sig = bytes(signature_placeholder)

    parts: list[bytes] = [
        MAGIC,
        struct.pack("!H", VERSION_V1),
        struct.pack("!I", len(payloads)),
    ]
    for p in payloads:
        raw = bytes(p)
        parts.append(struct.pack("!I", len(raw)))
        parts.append(raw)
    parts.append(sig)
    return b"".join(parts)


def decode_batch_v1(data: bytes) -> BatchCapsuleV1:
    """Parse capsule; raises BatchCapsuleError on corruption."""
    if len(data) < _HEADER_NO_SIG + SIGNATURE_RESERVED_BYTES:
        raise BatchCapsuleError("truncated: shorter than header + signature slot")

    off = 0
    if data[off : off + 4] != MAGIC:
        raise BatchCapsuleError("bad magic")
    off += 4
    ver = struct.unpack_from("!H", data, off)[0]
    off += 2
    if ver != VERSION_V1:
        raise BatchCapsuleError(f"unsupported version {ver}")
    count = struct.unpack_from("!I", data, off)[0]
    off += 4

    out: list[bytes] = []
    for _ in range(count):
        if off + 4 > len(data) - SIGNATURE_RESERVED_BYTES:
            raise BatchCapsuleError("truncated at length prefix")
        plen = struct.unpack_from("!I", data, off)[0]
        off += 4
        if off + plen > len(data) - SIGNATURE_RESERVED_BYTES:
            raise BatchCapsuleError("truncated in payload body")
        out.append(bytes(data[off : off + plen]))
        off += plen

    if off + SIGNATURE_RESERVED_BYTES != len(data):
        raise BatchCapsuleError("trailing bytes or length mismatch")

    sig = bytes(data[off : off + SIGNATURE_RESERVED_BYTES])
    return BatchCapsuleV1(version=ver, payloads=tuple(out), signature_reserved=sig)


def overhead_bytes_v1(n: int) -> int:
    """Fixed overhead excluding payload octets: header + per-item length words + sig slot."""
    if n < 0:
        raise ValueError("n must be non-negative")
    return _HEADER_NO_SIG + 4 * n + SIGNATURE_RESERVED_BYTES
