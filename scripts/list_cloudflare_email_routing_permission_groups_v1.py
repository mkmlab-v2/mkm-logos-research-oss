#!/usr/bin/env python3
"""List Cloudflare token permission groups for Email Routing (no secrets printed)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

OUT = ROOT / "reports" / "cloudflare_email_routing_permission_groups_latest.json"


def main() -> int:
    tok, src = resolve_cloudflare_token()
    if not tok:
        print("no CLOUDFLARE_API_TOKEN", file=sys.stderr)
        return 1
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/user/tokens/permission_groups",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body[:500]}", file=sys.stderr)
        return 2
    if not payload.get("success"):
        print("API failed", payload.get("errors"), file=sys.stderr)
        return 2
    groups = payload.get("result") or []
    needles = ("email routing", "zone read", "zone dns")
    hits = []
    for g in groups:
        name = (g.get("name") or "").lower()
        if any(n in name for n in needles):
            hits.append(
                {
                    "id": g.get("id"),
                    "name": g.get("name"),
                    "scopes": g.get("scopes"),
                }
            )
    out = {
        "schema": "cloudflare_email_routing_permission_groups_v1",
        "token_source": src,
        "hits": hits,
        "recommended_ids_note": "Use ids in create-via-api or permissionGroupIds URL if supported",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
