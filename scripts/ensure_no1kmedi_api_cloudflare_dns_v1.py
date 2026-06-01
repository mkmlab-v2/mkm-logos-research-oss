#!/usr/bin/env python3
"""Ensure api.no1kmedi.com A -> VPS IP (proxied). Read SSL mode. No Bot Fight API (dashboard)."""
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
HOST = "api.no1kmedi.com"
ORIGIN_IP = "148.230.97.246"
OUT = ROOT / "reports" / "no1kmedi_api_cf_automation_probe_latest.json"


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
    dry = "--dry-run" in sys.argv
    force = "--require-api-write" in sys.argv
    live = public_dns_live()
    tok, tok_src = resolve_cloudflare_token(extra_keys=("MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN",))
    if not tok:
        print("MKM_CLOUDFLARE_NO1KMEDI_DNS_TOKEN or CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    out: dict = {
        "schema": "no1kmedi_api_cf_automation_probe_v1",
        "host": HOST,
        "origin_ip": ORIGIN_IP,
        "zone_id": ZONE_ID,
        "dry_run": dry,
        "public_dns_live": live,
        "require_api_write": force,
        "token_source": tok_src,
    }
    if live and not force and not dry:
        out["dns_action"] = "skipped_public_live"
        out["dns_result"] = True
        out["agent_note"] = "api.no1kmedi.com public /health OK — API ensure skipped"
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0
    verify = _api(tok, "GET", "/user/tokens/verify")
    out["token_verify"] = verify.get("success")
    if not verify.get("success"):
        out["errors"] = verify.get("errors")
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 2

    lr = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name={HOST}")
    recs = lr.get("result") or []
    out["dns_before"] = [
        {"id": r.get("id"), "type": r.get("type"), "content": r.get("content"), "proxied": r.get("proxied")}
        for r in recs
    ]
    a_recs = [r for r in recs if r.get("type") == "A"]
    aaaa_recs = [r for r in recs if r.get("type") == "AAAA"]
    body = {"type": "A", "name": HOST, "content": ORIGIN_IP, "proxied": True, "ttl": 1}
    deleted: list[dict] = []
    if not dry:
        for r in aaaa_recs:
            dr = _api(tok, "DELETE", f"/zones/{ZONE_ID}/dns_records/{r['id']}")
            deleted.append({"type": "AAAA", "content": r.get("content"), "ok": dr.get("success")})
        for r in a_recs:
            if r.get("content") == ORIGIN_IP and r.get("proxied"):
                continue
            dr = _api(tok, "DELETE", f"/zones/{ZONE_ID}/dns_records/{r['id']}")
            deleted.append({"type": "A", "content": r.get("content"), "ok": dr.get("success")})
    if deleted:
        out["dns_deleted"] = deleted
    lr = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name={HOST}")
    recs = lr.get("result") or []
    a_recs = [r for r in recs if r.get("type") == "A" and r.get("content") == ORIGIN_IP and r.get("proxied")]
    if not a_recs:
        out["dns_action"] = "create"
        if not dry:
            cr = _api(tok, "POST", f"/zones/{ZONE_ID}/dns_records", body)
            out["dns_result"] = cr.get("success")
            out["dns_errors"] = cr.get("errors")
    else:
        out["dns_action"] = "ok"
        out["dns_result"] = True

    ssl = _api(tok, "GET", f"/zones/{ZONE_ID}/settings/ssl")
    out["ssl_mode"] = (ssl.get("result") or {}).get("value")
    out["manual_required"] = [
        "Security: Bot Fight / JS Challenge bypass for api.no1kmedi.com (WAF custom rule or host-specific)",
        "If public still blocked after DNS: set SSL Flexible OR install Origin Certificate + Full (strict)",
    ]
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if out.get("dns_result", True) is not False else 3


if __name__ == "__main__":
    raise SystemExit(main())
