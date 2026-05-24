#!/usr/bin/env python3
"""Ensure mkmlab.space apex A (+ optional www CNAME) point to Hostinger VPS origin (Cloudflare proxied)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from mkm_cloudflare_token_v1 import resolve_cloudflare_token, token_fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "cloudflare_dns_ensure_mkmlab_space_latest.json"
ZONE = "mkmlab.space"
DEFAULT_ORIGIN_IP = "148.230.97.246"  # JEMA_AI_DOMAIN_POINTER / srv1101456
ZONE_META = (
    ROOT / "scripts" / "data" / "hostinger_full_exit" / "mkmlab_cloudflare_zone_v1.json"
)


def _token() -> tuple[str, str]:
    return resolve_cloudflare_token()


def _api(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except json.JSONDecodeError:
            detail = {"raw": raw[:400]}
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {detail}") from exc


def _probe_dns_read(token: str, zone_id: str) -> None:
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?per_page=1"
    _api("GET", url, token)


def _zone_id_from_fixture() -> str:
    env = os.environ.get("CLOUDFLARE_MKMLAB_ZONE_ID", "").strip()
    if env:
        return env
    if ZONE_META.is_file():
        doc = json.loads(ZONE_META.read_text(encoding="utf-8"))
        zid = (doc.get("zone_id") or "").strip()
        if zid:
            return zid
    inv = ROOT / "reports" / "cloudflare_op5_zone_inventory_v1.json"
    if inv.is_file():
        doc = json.loads(inv.read_text(encoding="utf-8"))
        for row in doc.get("zones") or []:
            if isinstance(row, (list, tuple)) and len(row) >= 2 and row[0] == ZONE:
                return str(row[1])
    return ""


def _zone_id(token: str, explicit: str = "") -> str:
    if explicit:
        return explicit
    fixed = _zone_id_from_fixture()
    if fixed:
        return fixed
    import urllib.parse

    q = urllib.parse.quote(ZONE)
    url = f"https://api.cloudflare.com/client/v4/zones?name={q}"
    j = _api("GET", url, token)
    res = j.get("result") or []
    if res:
        return str(res[0]["id"])
    page = 1
    while True:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
        j = _api("GET", url, token)
        for z in j.get("result") or []:
            if (z.get("name") or "").lower() == ZONE:
                return str(z["id"])
        total_pages = (j.get("result_info") or {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1
    raise RuntimeError(f"zone not found in Cloudflare: {ZONE}")


def _list_records(token: str, zone_id: str, rtype: str, name: str) -> list[dict]:
    import urllib.parse

    fq = ZONE if not name or name == "@" else (f"{name}.{ZONE}" if "." not in name else name)
    url = (
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        f"?type={rtype}&name={urllib.parse.quote(fq)}"
    )
    j = _api("GET", url, token)
    return list(j.get("result") or [])


def _upsert_a(token: str, zone_id: str, ip: str, proxied: bool = True) -> str:
    existing = _list_records(token, zone_id, "A", "@")
    body = {
        "type": "A",
        "name": ZONE,
        "content": ip,
        "proxied": proxied,
        "ttl": 1,
    }
    if existing:
        rid = existing[0]["id"]
        _api(
            "PATCH",
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rid}",
            token,
            body,
        )
        return "patched"
    _api(
        "POST",
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        token,
        body,
    )
    return "created"


def _upsert_www_cname(token: str, zone_id: str, proxied: bool = True) -> str:
    existing = _list_records(token, zone_id, "CNAME", "www")
    body = {
        "type": "CNAME",
        "name": "www",
        "content": ZONE,
        "proxied": proxied,
        "ttl": 1,
    }
    if existing:
        rid = existing[0]["id"]
        _api(
            "PATCH",
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rid}",
            token,
            body,
        )
        return "patched"
    _api(
        "POST",
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        token,
        body,
    )
    return "created"


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--origin-ip", default=os.environ.get("MKMLAB_VPS_ORIGIN_IP", DEFAULT_ORIGIN_IP))
    p.add_argument("--what-if", action="store_true")
    p.add_argument("--skip-www", action="store_true")
    p.add_argument("--zone-id", default="", help="Override when zones?name= is scoped away")
    args = p.parse_args()

    token, token_source = _token()
    payload: dict = {
        "schema": "cloudflare_dns_ensure_mkmlab_space_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "zone": ZONE,
        "origin_ip": args.origin_ip,
        "token_present": bool(token),
        "token_source": token_source,
        "token_fp": token_fingerprint(token) if token else None,
        "actions": [],
        "ok": False,
    }
    if not token:
        payload["error"] = "CLOUDFLARE_API_TOKEN missing (User/.env; see mkm_cloudflare_token_v1.py)"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}, ensure_ascii=False))
        return 2

    if args.what_if:
        payload["actions"] = [
            {"planned": "A", "name": ZONE, "content": args.origin_ip, "proxied": True},
        ]
        if not args.skip_www:
            payload["actions"].append(
                {"planned": "CNAME", "name": f"www.{ZONE}", "content": ZONE, "proxied": True}
            )
        payload["ok"] = True
    else:
        try:
            zid = _zone_id(token, args.zone_id.strip())
            payload["zone_id"] = zid
            _probe_dns_read(token, zid)
            payload["actions"].append({"apex_a": _upsert_a(token, zid, args.origin_ip)})
            if not args.skip_www:
                payload["actions"].append({"www_cname": _upsert_www_cname(token, zid)})
            payload["ok"] = True
        except (urllib.error.HTTPError, RuntimeError) as exc:
            msg = str(exc)
            payload["error"] = msg
            if "HTTP 403" in msg and "dns_records" in msg:
                payload["error_class"] = "dns_permission_403"
                payload["fix"] = (
                    "CLOUDFLARE_API_TOKEN lacks Zone.DNS Read+Edit (Tunnel/Zone-Read-only tokens "
                    "cannot PATCH DNS). Create a DNS token in Cloudflare dashboard, set .env, run "
                    "projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1, "
                    "restart Cursor. Probe: py scripts/probe_mkmlab_cloudflare_dns_token_v1.py"
                )
            elif "zone not found" in msg:
                payload["error_class"] = "zone_not_visible"
            payload["ok"] = False

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "out": str(OUT)}, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
