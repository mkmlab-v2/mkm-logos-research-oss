#!/usr/bin/env python3
"""Secure payload envelope v1 contract (AES-256-GCM + compression side-channel payload).

This module defines the canonical interface and envelope shape. It does not tie
the runtime to a specific crypto backend or KMS implementation.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol


SCHEMA_NAME = "mkm_secure_payload_envelope_v1"
SCHEMA_VERSION = "1.0.0"
CONTENT_TYPE = "application/vnd.mkm.l1-side-channel+msgpack"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw.encode("ascii"))


@dataclass(frozen=True)
class EnvelopeHeader:
    schema_version: str
    api_contract_version: str
    track: str
    key_id: str
    codec_variant: str
    content_type: str
    created_at_utc: str
    wrapped_dek_b64: str | None = None
    meta_hash_sha256: str | None = None


@dataclass(frozen=True)
class SecurePayloadEnvelope:
    schema: str
    header: EnvelopeHeader
    aad_b64: str
    nonce_b64: str
    ciphertext_b64: str
    tag_b64: str

    def to_dict(self) -> dict[str, object]:
        body = asdict(self)
        body["header"] = asdict(self.header)
        return body


class AesGcmProvider(Protocol):
    """Pluggable AES-256-GCM provider.

    Implementations can bind to local crypto libs and/or KMS/Vault envelope
    semantics, as long as this interface is preserved.
    """

    def encrypt(
        self,
        *,
        key_id: str,
        plaintext: bytes,
        aad: bytes,
        track: str,
    ) -> tuple[bytes, bytes, bytes]:
        """Returns (nonce, ciphertext, tag)."""

    def decrypt(
        self,
        *,
        key_id: str,
        nonce: bytes,
        ciphertext: bytes,
        tag: bytes,
        aad: bytes,
        track: str,
    ) -> bytes:
        """Raises on tag mismatch or key-access policy violation."""


def canonical_aad_bytes(header: EnvelopeHeader) -> bytes:
    """Canonicalized JSON bytes used as AES-GCM AAD."""
    material = {
        "schema_version": header.schema_version,
        "api_contract_version": header.api_contract_version,
        "track": header.track,
        "key_id": header.key_id,
        "codec_variant": header.codec_variant,
        "content_type": header.content_type,
        "created_at_utc": header.created_at_utc,
        "wrapped_dek_b64": header.wrapped_dek_b64,
        "meta_hash_sha256": header.meta_hash_sha256,
    }
    return json.dumps(material, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_header(
    *,
    api_contract_version: str,
    track: str,
    key_id: str,
    codec_variant: str,
    wrapped_dek_b64: str | None = None,
    metadata_bytes: bytes | None = None,
) -> EnvelopeHeader:
    if track not in {"a_track", "b_track"}:
        raise ValueError("track must be one of: a_track, b_track")
    if codec_variant not in {"raw_msgpack", "zstd_msgpack"}:
        raise ValueError("codec_variant must be one of: raw_msgpack, zstd_msgpack")
    meta_hash = sha256(metadata_bytes).hexdigest() if metadata_bytes is not None else None
    return EnvelopeHeader(
        schema_version=SCHEMA_VERSION,
        api_contract_version=api_contract_version,
        track=track,
        key_id=key_id,
        codec_variant=codec_variant,
        content_type=CONTENT_TYPE,
        created_at_utc=datetime.now(UTC).isoformat(),
        wrapped_dek_b64=wrapped_dek_b64,
        meta_hash_sha256=meta_hash,
    )


def encrypt_envelope(
    *,
    provider: AesGcmProvider,
    key_id: str,
    track: str,
    codec_variant: str,
    payload_bytes: bytes,
    api_contract_version: str = "1.0.0",
    wrapped_dek_b64: str | None = None,
) -> SecurePayloadEnvelope:
    header = build_header(
        api_contract_version=api_contract_version,
        track=track,
        key_id=key_id,
        codec_variant=codec_variant,
        wrapped_dek_b64=wrapped_dek_b64,
        metadata_bytes=payload_bytes,
    )
    aad = canonical_aad_bytes(header)
    nonce, ciphertext, tag = provider.encrypt(
        key_id=key_id,
        plaintext=payload_bytes,
        aad=aad,
        track=track,
    )
    return SecurePayloadEnvelope(
        schema=SCHEMA_NAME,
        header=header,
        aad_b64=_b64url_encode(aad),
        nonce_b64=_b64url_encode(nonce),
        ciphertext_b64=_b64url_encode(ciphertext),
        tag_b64=_b64url_encode(tag),
    )


def decrypt_envelope(
    *,
    provider: AesGcmProvider,
    envelope: SecurePayloadEnvelope,
) -> bytes:
    if envelope.schema != SCHEMA_NAME:
        raise ValueError(f"unsupported schema: {envelope.schema}")
    aad = canonical_aad_bytes(envelope.header)
    if _b64url_encode(aad) != envelope.aad_b64:
        raise ValueError("AAD mismatch: envelope header does not match aad_b64")
    return provider.decrypt(
        key_id=envelope.header.key_id,
        nonce=_b64url_decode(envelope.nonce_b64),
        ciphertext=_b64url_decode(envelope.ciphertext_b64),
        tag=_b64url_decode(envelope.tag_b64),
        aad=aad,
        track=envelope.header.track,
    )
