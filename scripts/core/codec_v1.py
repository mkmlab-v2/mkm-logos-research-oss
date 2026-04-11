# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.75, L:0.55, K:0.88, M:0.5}
# Balance: 87
# Purpose: Isolated spike — prefix varint (zigzag offsets) + packed opcodes + rANS spike for skewed symbols.
# Keywords: codec, varint, zigzag, rANS, delta, zone_c
"""codec_v1 — isolated delta / offset encoding spike (Fact-Lock; not wired to router).

Components:
  - Unsigned LEB128-style prefix varints (7 data bits + continuation bit).
  - Zigzag for signed deltas (int → uint for varint).
  - Opcode stream: bit-packing with a leading ``bits_per`` byte (fractional bits per symbol).
  - Optional :func:`encode_opcodes_rans_spike` / :func:`decode_opcodes_rans_spike`: minimal rANS
    (fixed skewed frequency table) for opcode-only blobs — spike API, not mixed into bundle v1.

Wire layout for :func:`encode_delta_bundle_v1` (v1):
  version[1]      = 0x01
  count[uv]       = uvarint(number of offset/opcode pairs)
  offsets[uv×n]   = uvarint(zigzag(offset_i)) for each i
  opcodes[]       = ``bits_per`` byte + packed payload (see ``_encode_opcodes_bitpacked_with_header``)

This module is intentionally not imported by production compression paths until benchmarks isolate gains.
"""
from __future__ import annotations

import math
from typing import Sequence

VERSION_DELTA_BUNDLE_V1 = 1

# Isolated spike: with 1-byte zigzag limbs and 2-bit opcodes (0..3), wire stays ≤15 bytes for n≤9.
KILL_ZONE_MAX_PAIRS = 9

class CodecV1Error(ValueError):
    """Invalid encoded bytes or unsupported version."""


def encode_uvarint(n: int) -> bytes:
    """Encode non-negative int as unsigned LEB128 (prefix / continuation varint)."""
    if n < 0:
        raise ValueError("encode_uvarint expects n >= 0")
    out = bytearray()
    while n >= 0x80:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n & 0x7F)
    return bytes(out)


def decode_uvarint(data: bytes, pos: int = 0) -> tuple[int, int]:
    """Decode unsigned varint; returns (value, next_pos)."""
    shift = 0
    val = 0
    while True:
        if pos >= len(data):
            raise CodecV1Error("truncated uvarint")
        b = data[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return val, pos
        shift += 7
        if shift > 70:
            raise CodecV1Error("uvarint overflow")


def zigzag_encode(n: int) -> int:
    """Signed → unsigned for varint (portable)."""
    if n >= 0:
        return n << 1
    return ((-n) << 1) - 1


def zigzag_decode(z: int) -> int:
    return (z >> 1) ^ (-(z & 1))


def _bits_needed(max_symbol: int) -> int:
    if max_symbol < 0:
        raise ValueError("negative symbol")
    if max_symbol == 0:
        return 1
    return max(1, int(math.ceil(math.log2(max_symbol + 1))))


def _encode_opcodes_bitpacked_with_header(opcodes: Sequence[int]) -> bytes:
    if not opcodes:
        return bytes([0])
    m = max(int(x) for x in opcodes)
    for x in opcodes:
        v = int(x)
        if v < 0 or v > m:
            raise ValueError("opcode out of implied range")
    bits_per = _bits_needed(m)
    head = bytes([bits_per])
    total_bits = bits_per * len(opcodes)
    nbytes = (total_bits + 7) // 8
    body = bytearray(nbytes)
    bit_pos = 0
    for sym in opcodes:
        v = int(sym)
        for _ in range(bits_per):
            if v & 1:
                bi, bk = divmod(bit_pos, 8)
                body[bi] |= 1 << bk
            v >>= 1
            bit_pos += 1
    return head + bytes(body)


def _decode_opcodes_bitpacked_with_header(data: bytes, pos: int, count: int) -> tuple[tuple[int, ...], int]:
    if count == 0:
        if pos < len(data) and data[pos] == 0:
            return (), pos + 1
        return (), pos
    if pos >= len(data):
        raise CodecV1Error("truncated opcode header")
    bits_per = data[pos]
    pos += 1
    if bits_per == 0:
        return (), pos
    total_bits = bits_per * count
    nbytes = (total_bits + 7) // 8
    if pos + nbytes > len(data):
        raise CodecV1Error("truncated opcode body")
    raw = data[pos : pos + nbytes]
    pos += nbytes
    out: list[int] = []
    bit_pos = 0
    for _ in range(count):
        val = 0
        for i in range(bits_per):
            bi, bk = divmod(bit_pos, 8)
            if raw[bi] & (1 << bk):
                val |= 1 << i
            bit_pos += 1
        out.append(val)
    return tuple(out), pos


def encode_delta_bundle_v1(offsets: Sequence[int], opcodes: Sequence[int]) -> bytes:
    """Pack paired offsets (signed deltas) and opcodes with varint + bit-packed opcodes."""
    if len(offsets) != len(opcodes):
        raise ValueError("offsets and opcodes must have the same length")
    n = len(offsets)
    parts: list[bytes] = [bytes([VERSION_DELTA_BUNDLE_V1]), encode_uvarint(n)]
    for o in offsets:
        zu = zigzag_encode(int(o))
        parts.append(encode_uvarint(zu))
    parts.append(_encode_opcodes_bitpacked_with_header(opcodes))
    return b"".join(parts)


def decode_delta_bundle_v1(data: bytes) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Inverse of :func:`encode_delta_bundle_v1`."""
    if not data:
        raise CodecV1Error("empty")
    if data[0] != VERSION_DELTA_BUNDLE_V1:
        raise CodecV1Error(f"unsupported bundle version {data[0]!r}")
    pos = 1
    n, pos = decode_uvarint(data, pos)
    offsets: list[int] = []
    for _ in range(n):
        zu, pos = decode_uvarint(data, pos)
        offsets.append(zigzag_decode(zu))
    opcodes, pos = _decode_opcodes_bitpacked_with_header(data, pos, n)
    if pos != len(data):
        raise CodecV1Error("trailing bytes after bundle")
    return tuple(offsets), opcodes


def encode_opcodes_bitpacked(opcodes: Sequence[int]) -> bytes:
    """Bit-pack opcodes with a leading ``bits_per`` byte (standalone helper)."""
    return _encode_opcodes_bitpacked_with_header(opcodes)


def marginal_metadata_bytes_v1(offsets: Sequence[int], opcodes: Sequence[int]) -> int:
    """Byte length of the v1 delta bundle (isolated marginal metadata size)."""
    return len(encode_delta_bundle_v1(offsets, opcodes))


def baseline_fixed_u32_pairs_bytes(n: int) -> int:
    """Naive baseline: 4 bytes per offset + 4 bytes per opcode."""
    if n < 0:
        raise ValueError("n must be non-negative")
    return 8 * n


def savings_vs_u32_baseline(offsets: Sequence[int], opcodes: Sequence[int]) -> int:
    """Positive = fewer bytes than uint32×2n."""
    return baseline_fixed_u32_pairs_bytes(len(offsets)) - marginal_metadata_bytes_v1(offsets, opcodes)


# --- rANS spike (skewed frequencies, 4 symbols) -------------------------------------------
_RANS_FREQ4 = (230, 10, 8, 8)


def _rans_cumul(freqs: tuple[int, ...]) -> list[int]:
    c = [0]
    for f in freqs:
        c.append(c[-1] + f)
    return c


def encode_opcodes_rans_spike(opcodes: Sequence[int], freqs: tuple[int, ...] = _RANS_FREQ4) -> bytes:
    """Minimal rANS encoder for symbols in ``0..len(freqs)-1`` (reverse order, byte renormalization)."""
    syms = [int(x) for x in opcodes]
    for s in syms:
        if s < 0 or s >= len(freqs):
            raise ValueError("opcode out of rANS alphabet")
    M = sum(freqs)
    cum = _rans_cumul(freqs)
    if cum[-1] != M:
        raise ValueError("freqs must sum consistently")
    x = M
    out: list[int] = []
    for s in reversed(syms):
        f = freqs[s]
        start = cum[s]
        x = (x // f) * M + (x % f) + start
        while x >= 1 << 24:
            out.append(x & 0xFF)
            x >>= 8
    while x > 0:
        out.append(x & 0xFF)
        x >>= 8
    return bytes(reversed(out))


def decode_opcodes_rans_spike(data: bytes, count: int, freqs: tuple[int, ...] = _RANS_FREQ4) -> tuple[int, ...]:
    """Decode :func:`encode_opcodes_rans_spike` output."""
    M = sum(freqs)
    cum = _rans_cumul(freqs)
    if count == 0:
        if data:
            raise CodecV1Error("unexpected rANS payload for count=0")
        return ()
    if not data:
        raise CodecV1Error("empty rANS blob with count>0")
    x = 0
    for b in data:
        x = (x << 8) | b
    out: list[int] = []
    for _ in range(count):
        if x < M:
            raise CodecV1Error("bad rANS state")
        slot = x % M
        s = 0
        for i in range(len(freqs)):
            if slot < cum[i + 1]:
                s = i
                break
        else:
            raise CodecV1Error("rans slot")
        f = freqs[s]
        start = cum[s]
        x = (x // M) * f + (slot - start)
        out.append(s)
    return tuple(out)


def shannon_bits_lower_bound(freqs: Sequence[float], symbols: Sequence[int]) -> float:
    """Sum -log2(p[s]) for theoretical comparison (not wire bytes)."""
    total = float(sum(freqs))
    ps = [f / total for f in freqs]
    acc = 0.0
    for s in symbols:
        p = ps[int(s)]
        if p <= 0:
            raise ValueError("zero probability")
        acc += -math.log2(p)
    return acc
