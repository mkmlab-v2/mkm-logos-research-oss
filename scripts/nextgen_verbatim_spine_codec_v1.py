"""[HYPO] Verbatim spine codec — lossless utf-8 round-trip (B-track · NG-40 Phase 2)."""
from __future__ import annotations

import base64
import hashlib
import json
import struct
import zlib
from typing import Any


SCHEMA = "verbatim_spine_packet_v1"
BINARY_MAGIC = b"MKVS"
BINARY_VERSION = 1
CODEC_RAW = 0
CODEC_ZLIB = 1
BINARY_HEADER_LEN = 42  # magic(4) + ver(1) + codec(1) + utf8_len(4) + sha256(32)


def spine_sha256_utf8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verbatim_spine_encode(raw: str) -> dict[str, Any]:
    """Build spine packet; smaller of raw utf-8 vs zlib."""
    payload = raw.encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    z = zlib.compress(payload, level=9)
    if len(z) < len(payload):
        body = z
        codec = "zlib_utf8"
    else:
        body = payload
        codec = "raw_utf8"
    return {
        "schema": SCHEMA,
        "codec": codec,
        "utf8_len": len(payload),
        "payload_b64": base64.b64encode(body).decode("ascii"),
        "sha256": digest,
    }


def verbatim_spine_decode(packet: dict[str, Any]) -> str:
    if packet.get("schema") != SCHEMA:
        raise ValueError(f"unexpected spine schema: {packet.get('schema')}")
    codec = packet.get("codec")
    body = base64.b64decode(str(packet.get("payload_b64") or ""))
    if codec == "zlib_utf8":
        payload = zlib.decompress(body)
    elif codec == "raw_utf8":
        payload = body
    else:
        raise ValueError(f"unsupported spine codec: {codec}")
    digest = hashlib.sha256(payload).hexdigest()
    expected = str(packet.get("sha256") or "")
    if expected and digest != expected:
        raise ValueError("spine sha256 mismatch")
    return payload.decode("utf-8")


def spine_packet_json_bytes(packet: dict[str, Any]) -> int:
    return len(json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def spine_packet_body_bytes(packet: dict[str, Any]) -> int:
    """Compressed/raw utf-8 body only (no JSON envelope) — design reference."""
    return len(base64.b64decode(str(packet.get("payload_b64") or "")))


def verbatim_spine_packet_to_binary(packet: dict[str, Any]) -> bytes:
    """Billable spine envelope: MKVS header + sha256 + zlib/raw body (no JSON/base64)."""
    if packet.get("schema") != SCHEMA:
        raise ValueError(f"unexpected spine schema: {packet.get('schema')}")
    codec = packet.get("codec")
    codec_id = CODEC_ZLIB if codec == "zlib_utf8" else CODEC_RAW
    body = base64.b64decode(str(packet.get("payload_b64") or ""))
    digest = bytes.fromhex(str(packet.get("sha256") or ""))
    if len(digest) != 32:
        raise ValueError("spine sha256 must be 32 bytes hex")
    utf8_len = int(packet.get("utf8_len") or 0)
    return (
        BINARY_MAGIC
        + bytes([BINARY_VERSION, codec_id])
        + struct.pack(">I", utf8_len)
        + digest
        + body
    )


def verbatim_spine_decode_binary(blob: bytes) -> str:
    if len(blob) < BINARY_HEADER_LEN or blob[:4] != BINARY_MAGIC:
        raise ValueError("invalid spine binary magic")
    version, codec_id = blob[4], blob[5]
    if version != BINARY_VERSION:
        raise ValueError(f"unsupported spine binary version: {version}")
    utf8_len = struct.unpack(">I", blob[6:10])[0]
    digest = blob[10:42]
    body = blob[42:]
    if codec_id == CODEC_ZLIB:
        payload = zlib.decompress(body)
    elif codec_id == CODEC_RAW:
        payload = body
    else:
        raise ValueError(f"unsupported spine binary codec_id: {codec_id}")
    if len(payload) != utf8_len:
        raise ValueError("spine binary utf8_len mismatch")
    if hashlib.sha256(payload).digest() != digest:
        raise ValueError("spine binary sha256 mismatch")
    return payload.decode("utf-8")


def spine_packet_binary_bytes(packet: dict[str, Any]) -> int:
    return len(verbatim_spine_packet_to_binary(packet))


def char_saving_rate(raw: str, stored_bytes: int) -> float:
    raw_len = max(1, len(raw.encode("utf-8")))
    return round(1.0 - (stored_bytes / raw_len), 6)
