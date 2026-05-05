#!/usr/bin/env python3
"""Key resolver abstraction for secure payload envelope providers."""

from __future__ import annotations

import base64
import json
import os
import shlex
import subprocess
from typing import Protocol


class TrackKeyResolver(Protocol):
    def resolve_key(self, *, track: str) -> bytes:
        """Returns a 32-byte AES-256 key for the given track."""


class EnvTrackKeyResolver:
    """Default resolver: keys from process environment."""

    def resolve_key(self, *, track: str) -> bytes:
        if track == "a_track":
            raw = os.environ.get("MKM_ENVELOPE_A_TRACK_KEY_B64", "").strip()
        elif track == "b_track":
            raw = os.environ.get("MKM_ENVELOPE_B_TRACK_KEY_B64", "").strip()
        else:
            raise ValueError("track must be one of: a_track, b_track")
        if not raw:
            raise RuntimeError(f"missing key env for track={track}")
        return _decode_track_key_b64(raw, track=track)


class ExternalKmsTrackKeyResolver:
    """External key hook for Vault/KMS integration.

    Supported source contracts (first available wins):
    1) Command hook:
       - MKM_ENVELOPE_EXTERNAL_KEY_CMD="python scripts/fetch_key.py"
       - command prints one base64url key to stdout
       - MKM_ENVELOPE_KEY_TRACK env is injected ("a_track"|"b_track")
    2) JSON key file:
       - MKM_ENVELOPE_EXTERNAL_KEY_FILE="path/to/key_map.json"
       - schema: {"a_track":"<b64url>", "b_track":"<b64url>"}
    """

    def resolve_key(self, *, track: str) -> bytes:
        if track not in {"a_track", "b_track"}:
            raise ValueError("track must be one of: a_track, b_track")
        raw = self._resolve_from_command(track=track)
        if raw:
            return _decode_track_key_b64(raw, track=track)
        raw = self._resolve_from_json_file(track=track)
        if raw:
            return _decode_track_key_b64(raw, track=track)
        raise RuntimeError(
            "external key resolver returned no key; configure MKM_ENVELOPE_EXTERNAL_KEY_CMD "
            "or MKM_ENVELOPE_EXTERNAL_KEY_FILE"
        )

    @staticmethod
    def _resolve_from_command(*, track: str) -> str:
        cmd = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_CMD", "").strip()
        if not cmd:
            return ""
        args = shlex.split(cmd, posix=False)
        if not args:
            return ""
        env = os.environ.copy()
        env["MKM_ENVELOPE_KEY_TRACK"] = track
        out = subprocess.run(args, capture_output=True, text=True, check=True, env=env)
        return out.stdout.strip()

    @staticmethod
    def _resolve_from_json_file(*, track: str) -> str:
        path = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_FILE", "").strip()
        if not path:
            return ""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            raise RuntimeError(f"failed to read external key file: {path}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("external key file must be an object map")
        raw = data.get(track)
        if raw is None:
            return ""
        return str(raw).strip()


def _decode_track_key_b64(raw: str, *, track: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as exc:
        raise RuntimeError(f"invalid base64 key for track={track}") from exc
    if len(key) != 32:
        raise RuntimeError(f"AES-256 key must be 32 bytes for track={track}")
    return key

