#!/usr/bin/env python3
"""Command adapter for MKM secure envelope external key resolution.

Usage (resolver command hook):
  set MKM_ENVELOPE_EXTERNAL_KEY_CMD=py scripts/fetch_secure_envelope_key_adapter.py

Required env injected by resolver:
  MKM_ENVELOPE_KEY_TRACK: a_track | b_track

Adapter source precedence:
1) Track-specific command output
   - MKM_ENVELOPE_EXTERNAL_KEY_CMD_A_TRACK
   - MKM_ENVELOPE_EXTERNAL_KEY_CMD_B_TRACK
2) Track-specific env b64
   - MKM_ENVELOPE_EXTERNAL_KEY_B64_A_TRACK
   - MKM_ENVELOPE_EXTERNAL_KEY_B64_B_TRACK
3) JSON map file
   - MKM_ENVELOPE_EXTERNAL_KEY_FILE ({"a_track":"...", "b_track":"..."})

Output:
  Prints one base64url key to stdout. Non-zero exit on error.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys


def _track() -> str:
    track = os.environ.get("MKM_ENVELOPE_KEY_TRACK", "").strip().lower()
    if track not in {"a_track", "b_track"}:
        raise RuntimeError("MKM_ENVELOPE_KEY_TRACK must be a_track or b_track")
    return track


def _run_cmd(raw_cmd: str) -> str:
    args = shlex.split(raw_cmd, posix=False)
    if not args:
        return ""
    out = subprocess.run(args, capture_output=True, text=True, check=True, env=os.environ.copy())
    return out.stdout.strip()


def _resolve_from_track_command(track: str) -> str:
    if track == "a_track":
        cmd = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_CMD_A_TRACK", "").strip()
    else:
        cmd = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_CMD_B_TRACK", "").strip()
    if not cmd:
        return ""
    return _run_cmd(cmd)


def _resolve_from_track_env(track: str) -> str:
    if track == "a_track":
        return os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_B64_A_TRACK", "").strip()
    return os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_B64_B_TRACK", "").strip()


def _resolve_from_file(track: str) -> str:
    path = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_FILE", "").strip()
    if not path:
        return ""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError("MKM_ENVELOPE_EXTERNAL_KEY_FILE must contain object map")
    raw = data.get(track)
    return str(raw).strip() if raw is not None else ""


def main() -> int:
    try:
        track = _track()
        key = _resolve_from_track_command(track)
        if not key:
            key = _resolve_from_track_env(track)
        if not key:
            key = _resolve_from_file(track)
        if not key:
            raise RuntimeError(f"no key source resolved for track={track}")
        sys.stdout.write(key)
        return 0
    except Exception as exc:
        sys.stderr.write(f"[fetch_secure_envelope_key_adapter] {type(exc).__name__}: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

