#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime lock integrity checks for dimensional projection artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from threading import Lock

_LOCK = Lock()
_VERIFIED = False


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _runtime_lock_path() -> Path:
    env = os.getenv("DIMENSIONAL_PROJECTION_RUNTIME_LOCK_MANIFEST", "").strip()
    if env:
        return Path(env)
    return Path("C:/workspace/reports/dimensional_projection_bridge/freeze/runtime_lock_manifest_latest.json")


def enforce_runtime_lock() -> None:
    global _VERIFIED
    enforce = os.getenv("DIMENSIONAL_PROJECTION_ENFORCE_LOCK", "").strip().lower()
    if enforce in {"0", "false", "no", "off"}:
        return
    lock_path = _runtime_lock_path()
    if enforce in {"", "auto"} and (not lock_path.is_file()):
        return
    if _VERIFIED:
        return
    with _LOCK:
        if _VERIFIED:
            return
        if not lock_path.is_file():
            raise RuntimeError(f"runtime lock manifest missing: {lock_path}")
        payload = json.loads(lock_path.read_text(encoding="utf-8-sig"))
        checks = payload.get("checksums", {})
        refs = payload.get("refs", {})
        if not isinstance(checks, dict) or not isinstance(refs, dict):
            raise RuntimeError("runtime lock manifest invalid schema")
        required = ("active_overrides", "active_policies", "active_scorer")
        for key in required:
            p = Path(str(refs.get(key, "")))
            expected = str(checks.get(key, ""))
            if not p.is_file():
                raise RuntimeError(f"runtime lock target missing: {p}")
            if not expected:
                raise RuntimeError(f"runtime lock checksum missing: {key}")
            actual = _sha256(p)
            if actual != expected:
                raise RuntimeError(f"runtime lock checksum mismatch: {key}")
        _VERIFIED = True

