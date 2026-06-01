#!/usr/bin/env python3
"""Probe .env Cloudflare tokens for no1kmedi zone DNS write (no secrets printed)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from no1kmedi_public_dns_status_v1 import public_dns_live  # noqa: E402

ZONE_ID = "1516522160411707c33f84e145416a53"
ORIGIN = "148.230.97.246"
HOST = "research.no1kmedi.com"
OUT = ROOT / "reports" / "no1kmedi_cf_dns_token_probe_latest.json"


def _load_env_tokens() -> dict[str, str]:
    found: dict[str, str] = {}
    priority = ("MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN", "CLOUDFLARE_API_TOKEN", "CF_API_TOKEN", "CLOUDFLARE_RULESETS_API_TOKEN")
    env_path = ROOT / ".env"
    if env_path.is_file():
        raw: dict[str, str] = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if ("CLOUDFLARE" in k or k == "CF_API_TOKEN") and len(v) > 10:
                raw[k] = v
        for k in priority:
            if k in raw:
                found[k] = raw[k]
        for k, v in raw.items():
            if k not in found:
                found[k] = v
    for k in list(found):
        os.environ.setdefault(k, found[k])
    return found


def _api(tok: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"success": False, "errors": [{"message": str(e)}]}


def main() -> int:
    live = public_dns_live()
    force = "--require-api-write" in sys.argv
    tokens = _load_env_tokens()
    rows = []
    winner = None
    for name, tok in tokens.items():
        verify = _api(tok, "GET", "/user/tokens/verify")
        row = {"env_key": name, "verify": bool(verify.get("success"))}
        if row["verify"]:
            lr = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name={HOST}")
            exists = [
                r
                for r in (lr.get("result") or [])
                if r.get("type") == "A" and r.get("content") == ORIGIN
            ]
            if exists:
                row["dns"] = "already_exists"
                winner = name
            elif live and not force:
                row["dns"] = "not_required_public_live"
            else:
                cr = _api(
                    tok,
                    "POST",
                    f"/zones/{ZONE_ID}/dns_records",
                    {
                        "type": "A",
                        "name": HOST,
                        "content": ORIGIN,
                        "proxied": True,
                        "ttl": 1,
                    },
                )
                row["dns"] = "create_ok" if cr.get("success") else "create_fail"
                row["errors"] = cr.get("errors")
                if cr.get("success"):
                    winner = name
        rows.append(row)
    ops_ok = bool(winner) or (live and not force)
    out = {
        "schema": "no1kmedi_cf_dns_token_probe_v1",
        "public_dns_live": live,
        "require_api_write": force,
        "ops_ok": ops_ok,
        "rows": rows,
        "winner_env_key": winner,
        "agent_note": (
            "DNS token not required when public_dns_live and not --require-api-write"
            if live and not force
            else None
        ),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if ops_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
