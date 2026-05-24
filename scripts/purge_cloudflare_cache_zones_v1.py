#!/usr/bin/env python3
"""Purge Cloudflare cache for named zones (env CLOUDFLARE_API_TOKEN)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZONES = [
    ("jema-ai.com", "e64f17593ce48e31c2839b421c8bd4c0"),
    ("jemaai.cloud", "cf557dfa09436d998416ad849e73c0ec"),
]


def _load_dotenv_token() -> None:
    root = Path(__file__).resolve().parents[1]
    dotenv = root / ".env"
    if not dotenv.is_file():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and val:
            os.environ.setdefault("CLOUDFLARE_API_TOKEN", val)
            break


def main() -> int:
    _load_dotenv_token()
    tok = (
        os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1
    out = {"schema": "cloudflare_cache_purge_v1", "zones": []}
    ok_all = True
    for name, zid in ZONES:
        url = f"https://api.cloudflare.com/client/v4/zones/{zid}/purge_cache"
        body = json.dumps({"purge_everything": True}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {tok}",
                "Content-Type": "application/json",
            },
        )
        row = {"zone": name, "zone_id": zid}
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            row["http"] = resp.status
            row["success"] = bool(data.get("success"))
            row["errors"] = data.get("errors") or []
        except urllib.error.HTTPError as e:
            ok_all = False
            row["http"] = e.code
            row["success"] = False
            try:
                row["errors"] = json.loads(e.read().decode())
            except Exception:
                row["errors"] = [str(e)]
        out["zones"].append(row)
        print(f"{name}: http={row.get('http')} success={row.get('success')}")
    report = os.path.join(
        os.environ.get("MKM_WORKSPACE_ROOT", r"C:\workspace"),
        "reports",
        "cloudflare_cache_purge_latest.json",
    )
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {report}")
    return 0 if ok_all else 2


if __name__ == "__main__":
    raise SystemExit(main())
