"""Offline tests for ko_shorts_target_wav_lib_v1 resolve logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ko_shorts_target_wav_lib_v1 import (
    CASE_TO_FETCH_MEMBER,
    DEFAULT_AUTO_CASE,
    artifact_paths_for_case_v1,
    discover_delegated_wav_v1,
    resolve_target_wav_v1,
)


def test_artifact_paths_for_known_case():
    art = artifact_paths_for_case_v1("web_pansori")
    assert art["case_id"] == "web_pansori"
    assert "web_pansori" in art["spike_json"]
    assert art["mp4"].endswith(".mp4")


def test_resolve_explicit_wav(tmp_path: Path):
    wav = tmp_path / "my_clip.wav"
    wav.write_bytes(b"RIFF")
    out = resolve_target_wav_v1(wav=wav, auto=False)
    assert out["case_id"].startswith("target_")
    assert out["wav"] == wav
    assert out["wav_resolved_via"] == "explicit_path"


def test_resolve_auto_defaults_to_pansori_case():
    assert DEFAULT_AUTO_CASE == "web_pansori"
    assert CASE_TO_FETCH_MEMBER["web_pansori"] == "pansori"


def test_discover_delegated_from_sidecar(tmp_path: Path):
    wav = tmp_path / "cmd.wav"
    wav.write_bytes(b"RIFF")
    sidecar = tmp_path / "delegation.json"
    sidecar.write_text(
        json.dumps({"enabled": True, "wav": str(wav), "case_id": "target_cmd_v1"}),
        encoding="utf-8",
    )
    found = discover_delegated_wav_v1(sidecar_path=sidecar)
    assert found is not None
    assert found["wav"] == wav
    assert found["case_id"] == "target_cmd_v1"


def test_resolve_delegate_mode(tmp_path: Path):
    wav = tmp_path / "inbox.wav"
    wav.write_bytes(b"RIFF")
    sidecar = tmp_path / "delegation.json"
    sidecar.write_text(json.dumps({"wav": str(wav)}), encoding="utf-8")
    out = resolve_target_wav_v1(delegate=True, auto=False, delegation_sidecar=sidecar)
    assert out["wav"] == wav
    assert out["wav_resolved_via"] == "delegation_sidecar"


def test_resolve_unknown_case_without_wav_raises():
    with pytest.raises(ValueError, match="requires"):
        resolve_target_wav_v1(case_id="unknown_xyz", auto=False, refetch_missing=False)
