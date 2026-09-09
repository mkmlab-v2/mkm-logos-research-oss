from __future__ import annotations

import hashlib

import pytest

from experiments.file_native_retrieval_v0 import context_packet as cp


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packet(path, *, sha=None, revision="r1", **source_overrides):
    source = {
        "path": path.name,
        "expected_sha256": sha or _sha(path),
        **source_overrides,
    }
    return {
        "schema_version": cp.SCHEMA_VERSION,
        "packet_id": "packet-1",
        "repo_id": "repo-1",
        "revision": revision,
        "sources": [source],
        "verification_policy": cp.VERIFY_BEFORE_EVIDENCE,
    }


def test_valid_single_file_packet(tmp_path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("alpha\n", encoding="utf-8")
    packet = cp.ContextPacket.from_dict(_packet(path))
    assert packet.sources[0].path == "a.txt"
    assert packet.verification_policy == cp.VERIFY_BEFORE_EVIDENCE


def test_deterministic_serialization(tmp_path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("a\n", encoding="utf-8")
    b.write_text("b\n", encoding="utf-8")
    payload = _packet(a)
    payload["sources"] = [
        {"path": "b.txt", "expected_sha256": _sha(b)},
        {"path": "a.txt", "expected_sha256": _sha(a)},
    ]
    packet = cp.ContextPacket.from_dict(payload)
    first = cp.canonical_serialize(packet)
    second = cp.canonical_serialize(packet)
    assert first == second
    assert first.index('"a.txt"') < first.index('"b.txt"')


def test_valid_hash_rehydrates(tmp_path, monkeypatch) -> None:
    path = tmp_path / "a.txt"
    path.write_text("alpha\n", encoding="utf-8")
    monkeypatch.setattr(cp, "_repo_head", lambda root: None)
    result = cp.rehydrate_and_verify(_packet(path), tmp_path)
    assert result["status"] == "VERIFIED"
    assert result["evidence_eligible"] is True
    assert result["sources"][0]["content"] == "alpha\n"


def test_spoofed_hash_rejected_without_content(tmp_path, monkeypatch) -> None:
    path = tmp_path / "a.txt"
    path.write_text("alpha\n", encoding="utf-8")
    monkeypatch.setattr(cp, "_repo_head", lambda root: None)
    result = cp.rehydrate_and_verify(_packet(path, sha="0" * 64), tmp_path)
    assert result["status"] == "HASH_MISMATCH"
    assert result["evidence_eligible"] is False
    assert "content" not in result["sources"][0]


def test_modified_stale_source_rejected(tmp_path, monkeypatch) -> None:
    path = tmp_path / "a.txt"
    path.write_text("before\n", encoding="utf-8")
    payload = _packet(path)
    path.write_text("after\n", encoding="utf-8")
    monkeypatch.setattr(cp, "_repo_head", lambda root: None)
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "HASH_MISMATCH"


def test_missing_source_rejected(tmp_path, monkeypatch) -> None:
    path = tmp_path / "gone.txt"
    path.write_text("x", encoding="utf-8")
    payload = _packet(path)
    path.unlink()
    monkeypatch.setattr(cp, "_repo_head", lambda root: None)
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "MISSING_SOURCE"


def test_path_escape_rejected(tmp_path) -> None:
    payload = {
        "schema_version": cp.SCHEMA_VERSION,
        "packet_id": "packet-1",
        "repo_id": "repo-1",
        "revision": "r1",
        "sources": [
            {"path": "../escape.txt", "expected_sha256": "0" * 64}
        ],
        "verification_policy": cp.VERIFY_BEFORE_EVIDENCE,
    }
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "PATH_ESCAPE"


def test_exact_span_returned_only_after_verification(tmp_path, monkeypatch) -> None:
    path = tmp_path / "a.txt"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    monkeypatch.setattr(cp, "_repo_head", lambda root: None)
    result = cp.rehydrate_and_verify(
        _packet(path, line_start=2, line_end=3), tmp_path
    )
    source = result["sources"][0]
    assert source["status"] == "VERIFIED"
    assert source["returned_scope"] == "SPAN"
    assert source["content"] == "two\nthree\n"


def test_malformed_hash_rejected(tmp_path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    result = cp.rehydrate_and_verify(_packet(path, sha="not-a-sha"), tmp_path)
    assert result["status"] == "INVALID_PACKET"


def test_duplicate_source_coordinate_rejected(tmp_path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    source = {"path": "a.txt", "expected_sha256": _sha(path)}
    payload = _packet(path)
    payload["sources"] = [source, dict(source)]
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "INVALID_PACKET"


def test_source_verified_input_cannot_grant_verification(tmp_path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    payload = _packet(path, sha="0" * 64, source_verified=True)
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "INVALID_PACKET"
    assert result["evidence_eligible"] is False


def test_packet_revision_retained(tmp_path, monkeypatch) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cp, "_repo_head", lambda root: None)
    result = cp.rehydrate_and_verify(
        _packet(path, revision="rev-provenance-1"), tmp_path
    )
    assert result["revision"] == "rev-provenance-1"
    assert result["revision_status"] == "NOT_CHECKED"


def test_hash_verification_remains_authoritative_when_revision_matches(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    revision = "a" * 40
    monkeypatch.setattr(cp, "_repo_head", lambda root: revision)
    result = cp.rehydrate_and_verify(
        _packet(path, sha="0" * 64, revision=revision), tmp_path
    )
    assert result["revision_status"] == "MATCH"
    assert result["status"] == "HASH_MISMATCH"
    assert result["evidence_eligible"] is False


def test_revision_mismatch_blocks_evidence_even_with_verified_hash(
    tmp_path, monkeypatch
) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    monkeypatch.setattr(cp, "_repo_head", lambda root: "b" * 40)
    result = cp.rehydrate_and_verify(_packet(path, revision="a" * 40), tmp_path)
    assert result["sources"][0]["status"] == "VERIFIED"
    assert result["revision_status"] == "MISMATCH"
    assert result["status"] == "REVISION_MISMATCH"
    assert result["evidence_eligible"] is False


def test_invalid_span_rejected(tmp_path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x\n", encoding="utf-8")
    result = cp.rehydrate_and_verify(
        _packet(path, line_start=2, line_end=1), tmp_path
    )
    assert result["status"] == "INVALID_PACKET"


def test_absolute_windows_path_rejected(tmp_path) -> None:
    payload = {
        "schema_version": cp.SCHEMA_VERSION,
        "packet_id": "packet-1",
        "repo_id": "repo-1",
        "revision": "r1",
        "sources": [
            {"path": r"C:\outside.txt", "expected_sha256": "0" * 64}
        ],
        "verification_policy": cp.VERIFY_BEFORE_EVIDENCE,
    }
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "PATH_ESCAPE"


def test_unknown_verification_policy_rejected(tmp_path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("x", encoding="utf-8")
    payload = _packet(path)
    payload["verification_policy"] = "TRUST_PACKET"
    result = cp.rehydrate_and_verify(payload, tmp_path)
    assert result["status"] == "INVALID_PACKET"
