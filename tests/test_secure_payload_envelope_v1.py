from __future__ import annotations

import json

from scripts.core.secure_payload_envelope_v1 import (
    SCHEMA_NAME,
    SecurePayloadEnvelope,
    decrypt_envelope,
    encrypt_envelope,
)


class _FakeProvider:
    """Deterministic test double for interface-contract tests."""

    def encrypt(self, *, key_id: str, plaintext: bytes, aad: bytes, track: str):
        _ = (key_id, aad, track)
        nonce = b"n" * 12
        ciphertext = plaintext[::-1]
        tag = b"t" * 16
        return nonce, ciphertext, tag

    def decrypt(self, *, key_id: str, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes, track: str):
        _ = (key_id, aad, track)
        if nonce != b"n" * 12 or tag != b"t" * 16:
            raise ValueError("auth failed")
        return ciphertext[::-1]


def test_secure_payload_envelope_round_trip() -> None:
    provider = _FakeProvider()
    payload = b"side-channel-msgpack-payload"
    envelope = encrypt_envelope(
        provider=provider,
        key_id="kms/a-track/main-v1",
        track="a_track",
        codec_variant="zstd_msgpack",
        payload_bytes=payload,
    )
    assert envelope.schema == SCHEMA_NAME
    restored = decrypt_envelope(provider=provider, envelope=envelope)
    assert restored == payload


def test_secure_payload_schema_file_exists_and_has_required_fields() -> None:
    with open("docs/final/artifacts/schemas/mkm_secure_payload_envelope_v1.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["properties"]["schema"]["const"] == SCHEMA_NAME
    assert "header" in schema["required"]
    assert "tag_b64" in schema["required"]


def test_aad_tamper_detection() -> None:
    provider = _FakeProvider()
    payload = b"payload"
    env = encrypt_envelope(
        provider=provider,
        key_id="vault/b-track/dev-v1",
        track="b_track",
        codec_variant="raw_msgpack",
        payload_bytes=payload,
    )
    tampered = SecurePayloadEnvelope(
        schema=env.schema,
        header=env.header,
        aad_b64=env.aad_b64[:-2] + "xx",
        nonce_b64=env.nonce_b64,
        ciphertext_b64=env.ciphertext_b64,
        tag_b64=env.tag_b64,
    )
    try:
        decrypt_envelope(provider=provider, envelope=tampered)
        assert False, "expected aad mismatch"
    except ValueError as exc:
        assert "AAD mismatch" in str(exc)
