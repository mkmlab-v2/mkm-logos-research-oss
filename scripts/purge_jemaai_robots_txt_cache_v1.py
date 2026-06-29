#!/usr/bin/env python3
"""Purge jemaai.cloud /robots.txt from CF cache (needs Cache Purge scope)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
URL = "https://jemaai.cloud/robots.txt"


def main() -> int:
    tok, src = resolve_cloudflare_token()
    if not tok:
        print(json.dumps({"ok": False, "reason": "no_token"}))
        return 1
    body = json.dumps({"files": [URL]}).encode()
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/purge_cache",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
            print(json.dumps({"ok": True, "source": src, "http": resp.status, "payload": payload}))
            return 0
    except urllib.error.HTTPError as e:
        payload = json.loads(e.read().decode())
        print(json.dumps({"ok": False, "source": src, "http": e.code, "errors": payload.get("errors")}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
