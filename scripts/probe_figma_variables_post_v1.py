#!/usr/bin/env python3
"""Probe Figma Variables POST (expect 403 on Starter)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env(name: str) -> str | None:
    p = ROOT / ".env"
    if not p.is_file():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> int:
    token = _env("FIGMA_ACCESS_TOKEN") or _env("MKM_FIGMA_ACCESS_TOKEN")
    fk = _env("MKM_CLINIC_LOI_FIGMA_FILE_KEY")
    if not token or not fk:
        print(json.dumps({"ok": False, "error": "missing_token_or_file_key"}))
        return 1
    body = json.dumps({"variableCollections": [], "variables": [], "variableModes": []}).encode()
    req = urllib.request.Request(
        f"https://api.figma.com/v1/files/{fk}/variables",
        data=body,
        method="POST",
        headers={"X-Figma-Token": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(json.dumps({"ok": True, "http": resp.status}))
            return 0
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode("utf-8", errors="replace")[:400]
        print(json.dumps({"ok": False, "http": exc.code, "message": msg}))
        return 0 if exc.code else 1


if __name__ == "__main__":
    raise SystemExit(main())
