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
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402
from no1kmedi_public_dns_status_v1 import public_dns_live  # noqa: E402

ZONE_ID = "1516522160411707c33f84e145416a53"
ORIGIN_IP = "148.230.97.246"
# (fqdn, proxied) — www.clinic: grey cloud per SSOT (free plan 4th-level SSL)
DEFAULT_HOST_SPECS: list[tuple[str, bool]] = [
    ("research.no1kmedi.com", True),
    ("clinic.no1kmedi.com", True),
    ("www.clinic.no1kmedi.com", False),
    ("no1kmedi.com", True),
    ("www.no1kmedi.com", True),
]
OUT = ROOT / "reports" / "no1kmedi_research_clinic_cf_dns_latest.json"


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


def _ensure_a(tok: str, host: str, proxied: bool, dry: bool) -> dict:
    lr = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name={host}")
    recs = lr.get("result") or []
    a_ok = [
        r
        for r in recs
        if r.get("type") == "A"
        and r.get("content") == ORIGIN_IP
        and bool(r.get("proxied")) == proxied
    ]
    if a_ok:
        return {"host": host, "proxied": proxied, "action": "ok", "result": True}
    body = {"type": "A", "name": host, "content": ORIGIN_IP, "proxied": proxied, "ttl": 1}
    if dry:
        return {"host": host, "proxied": proxied, "action": "would_create", "result": True, "dry_run": True}
    for r in recs:
        if r.get("type") in ("A", "AAAA"):
            _api(tok, "DELETE", f"/zones/{ZONE_ID}/dns_records/{r['id']}")
    cr = _api(tok, "POST", f"/zones/{ZONE_ID}/dns_records", body)
    return {
        "host": host,
        "proxied": proxied,
        "action": "create",
        "result": bool(cr.get("success")),
        "errors": cr.get("errors"),
    }


def main() -> int:
    dry = "--dry-run" in sys.argv
    force = "--require-api-write" in sys.argv
    live = public_dns_live()
    host_specs = list(DEFAULT_HOST_SPECS)
    if "--hosts-only" in sys.argv:
        i = sys.argv.index("--hosts-only")
        names = sys.argv[i + 1 :]
        if not names:
            print("--hosts-only requires host names", file=sys.stderr)
            return 1
        host_specs = [(h, True) for h in names]

    tok, tok_src = resolve_cloudflare_token(extra_keys=("MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN",))
    if not tok:
        print("MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN or CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    out: dict = {
        "schema": "no1kmedi_research_clinic_cf_dns_v1",
        "zone_id": ZONE_ID,
        "origin_ip": ORIGIN_IP,
        "dry_run": dry,
        "public_dns_live": live,
        "require_api_write": force,
        "token_source": tok_src,
        "hosts": [],
    }
    if live and not force and not dry:
        for host, proxied in host_specs:
            out["hosts"].append(
                {
                    "host": host,
                    "proxied": proxied,
                    "action": "skipped_public_live",
                    "result": True,
                }
            )
        out["all_ok"] = True
        out["agent_note"] = "Public DNS/HTTPS OK — API ensure skipped (policy: no1kmedi_cf_dns_ops_policy_v1)"
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0
    verify = _api(tok, "GET", "/user/tokens/verify")
    if not verify.get("success"):
        out["token_verify"] = False
        out["errors"] = verify.get("errors")
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return 2

    failed = 0
    for host, proxied in host_specs:
        row = _ensure_a(tok, host, proxied, dry)
        out["hosts"].append(row)
        if not row.get("result"):
            failed += 1

    out["all_ok"] = failed == 0
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if failed == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
