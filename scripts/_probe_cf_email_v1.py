#!/usr/bin/env python3
"""One-off probe: DNS MX + email routing API (no secrets printed)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _tok() -> str:
    root = Path(__file__).resolve().parents[1]
    for line in (root / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("CLOUDFLARE_API_TOKEN=") or line.startswith("CF_API_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()


def _get(tok: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def main() -> int:
    tok = _tok()
    if not tok:
        print("no_token", file=sys.stderr)
        return 1
    zones = [
        ("no1kmedi.com", "1516522160411707c33f84e145416a53"),
        ("mkmlife.com", "259a847ea3643566383972ebd3ede918"),
    ]
    st, v = _get(tok, "/user/tokens/verify")
    print("token_verify", v.get("result", {}).get("status"), "http", st)
    for apex, zid in zones:
        print(f"\n=== {apex} zone_id={zid} ===")
        st, pl = _get(tok, f"/zones/{zid}/dns_records?type=MX")
        print("dns_mx", "success", pl.get("success"), "http", st)
        for rec in pl.get("result") or []:
            print(
                "  MX",
                rec.get("content"),
                "prio",
                rec.get("priority"),
                "id",
                rec.get("id"),
            )
        st, pl = _get(tok, f"/zones/{zid}/email/routing")
        print("email_routing", "success", pl.get("success"), "http", st, "errors", pl.get("errors"))
        if pl.get("success") and pl.get("result"):
            r = pl["result"]
            print("  enabled", r.get("enabled"), "status", r.get("status"))
        st, pl = _get(tok, f"/zones/{zid}/email/routing/rules")
        print("routing_rules", "success", pl.get("success"), "http", st)
        if pl.get("success"):
            for rule in pl.get("result") or []:
                matchers = rule.get("matchers") or []
                actions = rule.get("actions") or []
                print("  rule", rule.get("id"), "enabled", rule.get("enabled"), matchers, actions)
    acc = os.environ.get("MKM_CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not acc:
        for line in (Path(__file__).resolve().parents[1] / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("MKM_CLOUDFLARE_ACCOUNT_ID="):
                acc = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if acc:
        st, pl = _get(tok, f"/accounts/{acc}/email/routing/addresses")
        print("\n=== destination addresses ===")
        print("success", pl.get("success"), "http", st, "errors", pl.get("errors"))
        for a in pl.get("result") or []:
            print(" ", a.get("email"), "verified", a.get("verified"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
