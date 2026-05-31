#!/usr/bin/env python3
"""Ensure research.no1kmedi.com + clinic.no1kmedi.com (+ optional apex/www) A -> VPS (proxied)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZONE_ID = "1516522160411707c33f84e145416a53"
ORIGIN_IP = "148.230.97.246"
DEFAULT_HOSTS = [
    "research.no1kmedi.com",
    "clinic.no1kmedi.com",
    "no1kmedi.com",
    "www.no1kmedi.com",
]
OUT = ROOT / "reports" / "no1kmedi_research_clinic_cf_dns_latest.json"


def _load_token() -> str:
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CLOUDFLARE_API_TOKEN=") or line.startswith("CF_API_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return (os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN") or "").strip()


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


def _ensure_a(tok: str, host: str, dry: bool) -> dict:
    lr = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name={host}")
    recs = lr.get("result") or []
    a_ok = [
        r
        for r in recs
        if r.get("type") == "A" and r.get("content") == ORIGIN_IP and r.get("proxied")
    ]
    if a_ok:
        return {"host": host, "action": "ok", "result": True}
    body = {"type": "A", "name": host, "content": ORIGIN_IP, "proxied": True, "ttl": 1}
    if dry:
        return {"host": host, "action": "would_create", "result": True, "dry_run": True}
    for r in recs:
        if r.get("type") in ("A", "AAAA"):
            _api(tok, "DELETE", f"/zones/{ZONE_ID}/dns_records/{r['id']}")
    cr = _api(tok, "POST", f"/zones/{ZONE_ID}/dns_records", body)
    return {
        "host": host,
        "action": "create",
        "result": bool(cr.get("success")),
        "errors": cr.get("errors"),
    }


def main() -> int:
    dry = "--dry-run" in sys.argv
    hosts = DEFAULT_HOSTS
    if "--hosts-only" in sys.argv:
        i = sys.argv.index("--hosts-only")
        hosts = sys.argv[i + 1 :]
        if not hosts:
            print("--hosts-only requires host names", file=sys.stderr)
            return 1

    tok = _load_token()
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    out: dict = {
        "schema": "no1kmedi_research_clinic_cf_dns_v1",
        "zone_id": ZONE_ID,
        "origin_ip": ORIGIN_IP,
        "dry_run": dry,
        "hosts": [],
    }
    verify = _api(tok, "GET", "/user/tokens/verify")
    if not verify.get("success"):
        out["token_verify"] = False
        out["errors"] = verify.get("errors")
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return 2

    failed = 0
    for host in hosts:
        row = _ensure_a(tok, host, dry)
        out["hosts"].append(row)
        if not row.get("result"):
            failed += 1

    out["all_ok"] = failed == 0
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if failed == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
