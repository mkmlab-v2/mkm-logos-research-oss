#!/usr/bin/env python3
"""Probe which local CF tokens can read bot_management for jemaai.cloud."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import _read_dotenv_key, token_fingerprint  # noqa: E402

ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
KEYS = [
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
    "MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN",
    "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN",
]


def _get(key: str) -> str:
    v = os.environ.get(key, "").strip()
    if v:
        return v
    return _read_dotenv_key(key)


def probe(tok: str) -> dict:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/bot_management",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
            result = payload.get("result") or {}
            return {
                "http": resp.status,
                "success": payload.get("success"),
                "is_robots_txt_managed": result.get("is_robots_txt_managed"),
                "cf_robots_variant": result.get("cf_robots_variant"),
            }
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        return {"http": e.code, "success": False, "errors": payload.get("errors")}


def main() -> int:
    rows = []
    for key in KEYS:
        tok = _get(key)
        if not tok:
            continue
        rows.append({"key": key, "fp": token_fingerprint(tok), **probe(tok)})
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
