#!/usr/bin/env python3
"""L1 side-channel minimal payload wire codecs (research / bench).

Compares JSON UTF-8 proxy vs MessagePack vs Zstd(MessagePack) for the same
logical dict (swap_log, typo_patches, oov_stack only).

Optional deps: pip install msgpack zstandard
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CodecAvailability:
    msgpack: bool
    zstandard: bool


def codec_availability() -> CodecAvailability:
    mp = True
    try:
        import msgpack  # noqa: F401
    except ImportError:
        mp = False
    zs = True
    try:
        import zstandard  # noqa: F401
    except ImportError:
        zs = False
    return CodecAvailability(msgpack=mp, zstandard=zs)


def minimal_payload(side_channel: dict[str, Any]) -> dict[str, Any]:
    return {
        "swap_log": side_channel["swap_log"],
        "typo_patches": side_channel["typo_patches"],
        "oov_stack": side_channel["oov_stack"],
    }


def json_utf8_payload_bytes(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def msgpack_payload_bytes(payload: dict[str, Any]) -> bytes | None:
    try:
        import msgpack
    except ImportError:
        return None
    return msgpack.packb(payload, use_bin_type=True)


def zstd_compress(data: bytes, level: int = 3) -> bytes | None:
    try:
        import zstandard as zstd
    except ImportError:
        return None
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)


def encode_msgpack_zstd(payload: dict[str, Any], level: int = 3) -> bytes | None:
    raw = msgpack_payload_bytes(payload)
    if raw is None:
        return None
    z = zstd_compress(raw, level=level)
    return z


def decode_msgpack(blob: bytes) -> dict[str, Any]:
    import msgpack

    out = msgpack.unpackb(blob, raw=False, strict_map_key=False)
    if not isinstance(out, dict):
        raise TypeError("expected dict root")
    return out


def decode_msgpack_zstd(blob: bytes) -> dict[str, Any]:
    import zstandard as zstd

    dctx = zstd.ZstdDecompressor()
    raw = dctx.decompress(blob)
    return decode_msgpack(raw)


def merge_side_channel(mode: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "l1_side_channel_v1",
        "mode": mode,
        "swap_log": payload.get("swap_log", []),
        "typo_patches": payload.get("typo_patches", []),
        "oov_stack": payload.get("oov_stack", []),
    }


# Single-byte wire discriminator (after optional future versioning).
_WIRE_RAW_MSGPACK = 0
_WIRE_ZSTD_MSGPACK = 1


def encode_adaptive_msgpack(
    payload: dict[str, Any],
    *,
    zstd_min_raw_bytes: int = 64,
    zstd_level: int = 3,
) -> tuple[bytes, str]:
    """Pack minimal payload for wire: 1 tag byte + raw msgpack OR zstd(msgpack).

    If msgpack blob is smaller than ``zstd_min_raw_bytes``, or zstd does not
    shrink vs raw, sends raw msgpack (tag ``_WIRE_RAW_MSGPACK``).

    Returns (wire_bytes, variant) where variant is ``"raw"`` or ``"zstd"``.
    """
    raw = msgpack_payload_bytes(payload)
    if raw is None:
        raise RuntimeError("msgpack unavailable")
    if zstd_min_raw_bytes < 0:
        raise ValueError("zstd_min_raw_bytes must be >= 0")

    z = zstd_compress(raw, level=zstd_level)
    use_zstd = (
        z is not None
        and len(raw) >= zstd_min_raw_bytes
        and len(z) < len(raw)
    )
    if use_zstd:
        return bytes([_WIRE_ZSTD_MSGPACK]) + z, "zstd"
    return bytes([_WIRE_RAW_MSGPACK]) + raw, "raw"


def decode_adaptive_msgpack(wire: bytes) -> dict[str, Any]:
    """Inverse of :func:`encode_adaptive_msgpack` (same tag scheme)."""
    if len(wire) < 2:
        raise ValueError("wire too short")
    tag, body = wire[0], wire[1:]
    if tag == _WIRE_RAW_MSGPACK:
        return decode_msgpack(body)
    if tag == _WIRE_ZSTD_MSGPACK:
        return decode_msgpack_zstd(body)
    raise ValueError(f"unknown wire tag: {tag}")
