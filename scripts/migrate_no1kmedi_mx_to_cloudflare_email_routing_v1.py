#!/usr/bin/env python3
"""Point no1kmedi.com apex MX at Cloudflare Email Routing (DNS API only).

Use when Email Routing is enabled in dashboard but MX still points at Hostinger.
Requires CLOUDFLARE_API_TOKEN with Zone DNS Edit on no1kmedi.com.

Does NOT enable routing rules or destination verification — run setup_cloudflare_email_routing_v1.py
after token has Email Routing scopes, or finish in dashboard.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ZONE_ID = "1516522160411707c33f84e145416a53"
APEX = "no1kmedi.com"
CF_MX = [
    ("route1.mx.cloudflare.net", 35),
    ("route2.mx.cloudflare.net", 75),
    ("route3.mx.cloudflare.net", 90),
]
HOSTINGER_MX = ("mx1.hostinger.com", "mx2.hostinger.com")


def _load_token() -> str:
    root = Path(__file__).resolve().parents[1]
    for line in (root / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("CLOUDFLARE_API_TOKEN=") or line.startswith("CF_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()


def _api(tok: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def main() -> int:
    ap_dry = "--dry-run" in sys.argv
    tok = _load_token()
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    st, pl = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?type=MX")
    if not pl.get("success"):
        print("list MX failed", pl.get("errors"), file=sys.stderr)
        return 2

    records = pl.get("result") or []
    apex_mx = [r for r in records if (r.get("name") or "").rstrip(".").lower() == APEX]
    out: dict[str, Any] = {
        "schema": "migrate_no1kmedi_mx_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "apex": APEX,
        "dry_run": ap_dry,
        "before": [{"content": r.get("content"), "priority": r.get("priority"), "id": r.get("id")} for r in apex_mx],
        "actions": [],
    }

    cf_present = {r.get("content") for r in apex_mx} >= {h for h, _ in CF_MX}
    if cf_present and not any(h in (r.get("content") or "") for r in apex_mx for h in HOSTINGER_MX):
        print("OK: MX already Cloudflare Email Routing")
        return 0

    for rec in apex_mx:
        content = (rec.get("content") or "").lower()
        if "hostinger" in content or content not in {h for h, _ in CF_MX}:
            if ap_dry:
                out["actions"].append({"action": "delete", "id": rec.get("id"), "content": rec.get("content")})
            else:
                st, pl = _api(tok, "DELETE", f"/zones/{ZONE_ID}/dns_records/{rec['id']}")
                out["actions"].append(
                    {"action": "delete", "id": rec.get("id"), "http": st, "success": pl.get("success"), "errors": pl.get("errors")}
                )
                if not pl.get("success"):
                    print("delete failed", rec.get("content"), pl.get("errors"), file=sys.stderr)
                    return 3

    existing_cf = {(r.get("content"), r.get("priority")) for r in apex_mx}
    for host, prio in CF_MX:
        if (host, prio) in existing_cf:
            continue
        body = {"type": "MX", "name": APEX, "content": host, "priority": prio, "ttl": 1}
        if ap_dry:
            out["actions"].append({"action": "create", "body": body})
        else:
            st, pl = _api(tok, "POST", f"/zones/{ZONE_ID}/dns_records", body)
            out["actions"].append(
                {"action": "create", "body": body, "http": st, "success": pl.get("success"), "errors": pl.get("errors")}
            )
            if not pl.get("success"):
                print("create failed", host, pl.get("errors"), file=sys.stderr)
                return 4

    report = Path(__file__).resolve().parents[1] / "reports" / "no1kmedi_mx_migration_latest.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {report}")
    if ap_dry:
        print("DRY-RUN: would migrate MX to Cloudflare Email Routing")
        return 0
    print("OK: MX migrated to Cloudflare Email Routing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
