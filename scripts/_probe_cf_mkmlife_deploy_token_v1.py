#!/usr/bin/env python3
"""Probe mkmlife deploy token — Workers Scripts, KV, Zone Read, Workers Routes, User Details."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "646e42cf881ab43043c32430e99d9af4"
ZONE_ID = "259a847ea3643566383972ebd3ede918"
KV_NS = "2dc41cddcb1e417181bd2876916697bd"


def _read_token() -> str:
    env = ROOT / ".env"
    if not env.is_file():
        return ""
    keys = ("MKM_MKMLIFE_CF_DEPLOY_TOKEN", "CLOUDFLARE_API_TOKEN", "CF_API_TOKEN")
    found: dict[str, str] = {}
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k in keys:
            found[k] = v.strip().strip('"').strip("'")
    for k in keys:
        if found.get(k):
            return found[k]
    return ""


def _get(path: str, tok: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {"success": False, "errors": [{"message": str(exc)}]}


def main() -> int:
    tok = _read_token()
    if not tok:
        print("deploy_token: missing")
        return 1
    fp = f"{tok[:6]}...{tok[-4:]}"
    print(f"deploy_token_fp: {fp}")
    checks = [
        ("/user/tokens/verify", "token_verify", True),
        ("/user", "user_details", False),
        (f"/zones/{ZONE_ID}", "zone_read", True),
        (f"/zones/{ZONE_ID}/workers/routes", "workers_routes_list", False),
        (f"/accounts/{ACCOUNT}/workers/scripts", "workers_scripts_list", True),
        (f"/accounts/{ACCOUNT}/storage/kv/namespaces/{KV_NS}", "kv_namespace_read", True),
    ]
    ok_core = True
    routes_ok = False
    for path, label, required in checks:
        code, body = _get(path, tok)
        success = bool(body.get("success"))
        err_obj = (body.get("errors") or [{}])[0]
        err = err_obj.get("message", "")
        err_code = err_obj.get("code")
        print(f"{label}: http={code} success={success} err_code={err_code} err={err[:100]}")
        if label == "workers_routes_list" and success:
            routes_ok = True
        if required and not success:
            ok_core = False
    if ok_core and not routes_ok:
        print("workers_routes_missing: add Zone Workers Routes Edit on mkmlife.com zone to deploy token")
        return 2
    if not ok_core:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
