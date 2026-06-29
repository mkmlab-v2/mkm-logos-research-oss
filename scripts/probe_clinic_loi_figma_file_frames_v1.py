#!/usr/bin/env python3
"""Probe mkm-20260624 for Clinic LOI reference frame via Figma file API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env(name: str) -> str | None:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def main() -> int:
    token = _env("FIGMA_ACCESS_TOKEN") or _env("MKM_FIGMA_ACCESS_TOKEN")
    fk = _env("MKM_CLINIC_LOI_FIGMA_FILE_KEY")
    if not token or not fk:
        print(json.dumps({"ok": False, "error": "missing_credentials"}))
        return 1
    url = f"https://api.figma.com/v1/files/{fk}?depth=2"
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(json.dumps({"ok": False, "http": exc.code}))
        return 1

    frames: list[str] = []

    def walk(node: dict) -> None:
        if node.get("type") == "FRAME" and node.get("name"):
            frames.append(str(node["name"]))
        for child in node.get("children") or []:
            if isinstance(child, dict):
                walk(child)

    for page in data.get("document", {}).get("children") or []:
        if isinstance(page, dict):
            walk(page)

    clinic = [n for n in frames if "Clinic LOI" in n]
    out = {
        "ok": True,
        "file_key": fk,
        "clinic_loi_frames": clinic,
        "applied_likely": bool(clinic),
        "total_frames": len(frames),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
