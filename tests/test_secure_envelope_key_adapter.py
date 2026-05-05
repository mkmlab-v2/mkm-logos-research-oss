from __future__ import annotations

import base64
import json
import os
import subprocess
import sys


def _b64(ch: bytes) -> str:
    return base64.urlsafe_b64encode(ch * 32).decode("ascii")


def _run_adapter(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/fetch_secure_envelope_key_adapter.py"],
        cwd=".",
        env=env,
        capture_output=True,
        text=True,
    )


def test_adapter_reads_track_specific_env_key():
    env = os.environ.copy()
    env["MKM_ENVELOPE_KEY_TRACK"] = "a_track"
    env["MKM_ENVELOPE_EXTERNAL_KEY_B64_A_TRACK"] = _b64(b"A")
    cp = _run_adapter(env)
    assert cp.returncode == 0
    assert cp.stdout.strip() == _b64(b"A")


def test_adapter_reads_json_file_when_env_missing(tmp_path):
    key_file = tmp_path / "keys.json"
    key_file.write_text(json.dumps({"a_track": _b64(b"C"), "b_track": _b64(b"D")}), encoding="utf-8")
    env = os.environ.copy()
    env["MKM_ENVELOPE_KEY_TRACK"] = "b_track"
    env["MKM_ENVELOPE_EXTERNAL_KEY_FILE"] = str(key_file)
    cp = _run_adapter(env)
    assert cp.returncode == 0
    assert cp.stdout.strip() == _b64(b"D")
