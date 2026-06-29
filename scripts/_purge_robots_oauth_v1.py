#!/usr/bin/env python3
"""Purge jemaai.cloud/robots.txt using wrangler OAuth token."""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
URL = "https://jemaai.cloud/robots.txt"
WRANGLER_CFG = Path.home() / "AppData/Roaming/xdg.config/.wrangler/config/default.toml"


def _oauth() -> str:
    text = WRANGLER_CFG.read_text(encoding="utf-8")
    m = re.search(r'^oauth_token\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else ""


def main() -> int:
    tok = _oauth()
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
            print(resp.status, resp.read().decode()[:300])
            return 0
    except urllib.error.HTTPError as e:
        print(e.code, e.read().decode()[:300])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
