#!/usr/bin/env python3
"""Readiness checks for secure envelope external_kms mode.

Checks:
1) Required env contract for external_kms key resolution.
2) Optional command-hook smoke (MKM_ENVELOPE_EXTERNAL_KEY_CMD).
3) Optional HTTP smoke against /health and secure wire endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any


def _ok(msg: str) -> dict[str, Any]:
    return {"ok": True, "message": msg}


def _fail(msg: str) -> dict[str, Any]:
    return {"ok": False, "message": msg}


def check_env_contract() -> dict[str, Any]:
    provider = os.environ.get("MKM_ENVELOPE_KEY_PROVIDER", "").strip().lower()
    if provider != "external_kms":
        return _fail("MKM_ENVELOPE_KEY_PROVIDER must be external_kms")
    cmd = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_CMD", "").strip()
    key_file = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_FILE", "").strip()
    if not cmd and not key_file:
        return _fail("set MKM_ENVELOPE_EXTERNAL_KEY_CMD or MKM_ENVELOPE_EXTERNAL_KEY_FILE")
    ka = os.environ.get("MKM_ENVELOPE_A_TRACK_KEY_ID", "").strip()
    kb = os.environ.get("MKM_ENVELOPE_B_TRACK_KEY_ID", "").strip()
    if not ka or not kb:
        return _fail("MKM_ENVELOPE_A_TRACK_KEY_ID and MKM_ENVELOPE_B_TRACK_KEY_ID are required")
    return _ok("env contract ready")


def run_command_hook_smoke() -> dict[str, Any]:
    cmd = os.environ.get("MKM_ENVELOPE_EXTERNAL_KEY_CMD", "").strip()
    if not cmd:
        return _ok("command hook smoke skipped (MKM_ENVELOPE_EXTERNAL_KEY_CMD empty)")
    args = shlex.split(cmd, posix=False)
    if not args:
        return _fail("MKM_ENVELOPE_EXTERNAL_KEY_CMD is not executable")
    for track in ("a_track", "b_track"):
        env = os.environ.copy()
        env["MKM_ENVELOPE_KEY_TRACK"] = track
        try:
            cp = subprocess.run(args, env=env, capture_output=True, text=True, check=True)
        except Exception as exc:
            return _fail(f"command hook failed for {track}: {type(exc).__name__}")
        if not cp.stdout.strip():
            return _fail(f"command hook returned empty key for {track}")
    return _ok("command hook smoke passed")


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp is not None else "{}"
        parsed = json.loads(body) if body else {}
        return exc.code, parsed


def run_http_smoke(base_url: str) -> dict[str, Any]:
    health_url = base_url.rstrip("/") + "/health"
    code, payload = _http_json("GET", health_url)
    if code != 200:
        return _fail(f"/health failed: status={code}")
    mode = str(payload.get("secure_envelope", {}).get("key_provider_mode", ""))
    if mode != "external_kms":
        return _fail(f"/health key_provider_mode expected external_kms, got {mode!r}")
    for track in ("a_track", "b_track"):
        code, data = _http_json(
            "POST",
            base_url.rstrip("/") + "/v1/research/l1_side_channel/wire/secure",
            {
                "track": track,
                "side_channel": {"swap_log": [[0, 1]], "typo_patches": [], "oov_stack": []},
            },
        )
        if code != 200:
            return _fail(f"secure route failed for {track}: status={code}")
        flags = data.get("integrity_flags", {})
        header = data.get("envelope", {}).get("header", {})
        if not flags.get("secure_envelope"):
            return _fail(f"secure route missing secure_envelope flag for {track}")
        if header.get("track") != track:
            return _fail(f"secure route header.track mismatch for {track}")
    return _ok("http smoke passed")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="", help="Optional API base URL for live smoke, e.g. http://127.0.0.1:8010")
    args = p.parse_args()

    checks: list[tuple[str, dict[str, Any]]] = []
    checks.append(("env_contract", check_env_contract()))
    checks.append(("command_hook", run_command_hook_smoke()))
    if args.base_url.strip():
        checks.append(("http_smoke", run_http_smoke(args.base_url.strip())))

    ok = all(c[1]["ok"] for c in checks)
    out = {
        "schema": "secure_envelope_external_kms_readiness_v1",
        "overall_ok": ok,
        "checks": {name: result for name, result in checks},
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

