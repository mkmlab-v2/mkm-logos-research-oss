#!/usr/bin/env python3
"""Try bot_management update using wrangler OAuth token from default.toml."""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
WRANGLER_CFG = Path.home() / "AppData/Roaming/xdg.config/.wrangler/config/default.toml"


def _read_oauth() -> str:
    if not WRANGLER_CFG.is_file():
        return ""
    text = WRANGLER_CFG.read_text(encoding="utf-8")
    m = re.search(r'^oauth_token\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else ""


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def main() -> int:
    tok = _read_oauth()
    if not tok:
        print(json.dumps({"ok": False, "reason": "no_oauth_token"}))
        return 1
    st, verify = _api(tok, "GET", "/user/tokens/verify")
    print("verify", st, verify.get("success"))
    st, get_pl = _api(tok, "GET", f"/zones/{ZONE_ID}/bot_management")
    print("get", st, get_pl.get("success"), get_pl.get("errors"))
    if st != 200 or not get_pl.get("success"):
        return 1
    desired = dict(get_pl.get("result") or {})
    desired["is_robots_txt_managed"] = False
    desired["cf_robots_variant"] = "off"
    st2, put_pl = _api(tok, "PUT", f"/zones/{ZONE_ID}/bot_management", desired)
    print("put", st2, put_pl.get("success"), put_pl.get("errors"))
    with urllib.request.urlopen("https://jemaai.cloud/robots.txt", timeout=30) as resp:
        body = resp.read().decode()
    print("live_legacy", "Disallow: /legacy/" in body)
    print(body[:200])
    return 0 if "Disallow: /legacy/" in body else 2


if __name__ == "__main__":
    raise SystemExit(main())
