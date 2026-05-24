#!/usr/bin/env python3
"""Create or update farm.jema-ai.com DNS (CNAME → app.jema-ai.com, proxied)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZONE_NAME = "jema-ai.com"
ZONE_ID = "e64f17593ce48e31c2839b421c8bd4c0"
RECORD_NAME = "farm.jema-ai.com"
CNAME_TARGET = "app.jema-ai.com"


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


def _api(method: str, url: str, tok: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--zone-id", default=ZONE_ID)
    ap.add_argument("--cname-target", default=CNAME_TARGET)
    args = ap.parse_args()

    _load_dotenv_token()
    tok = (
        os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    list_url = (
        f"https://api.cloudflare.com/client/v4/zones/{args.zone_id}/dns_records"
        f"?type=CNAME&name={RECORD_NAME}"
    )
    try:
        listed = _api("GET", list_url, tok)
    except urllib.error.HTTPError as e:
        print(f"list failed http={e.code}", file=sys.stderr)
        return 2

    records = listed.get("result") or []
    payload = {
        "type": "CNAME",
        "name": RECORD_NAME,
        "content": args.cname_target,
        "proxied": True,
        "ttl": 1,
    }
    out = {
        "schema": "cloudflare_farm_jema_ai_dns_v1",
        "record_name": RECORD_NAME,
        "cname_target": args.cname_target,
        "zone_id": args.zone_id,
        "action": None,
    }

    if args.dry_run:
        out["action"] = "dry_run"
        out["existing_count"] = len(records)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    try:
        if records:
            rid = records[0]["id"]
            updated = _api(
                "PATCH",
                f"https://api.cloudflare.com/client/v4/zones/{args.zone_id}/dns_records/{rid}",
                tok,
                payload,
            )
            out["action"] = "updated"
            out["record_id"] = rid
            out["success"] = bool(updated.get("success"))
        else:
            created = _api(
                "POST",
                f"https://api.cloudflare.com/client/v4/zones/{args.zone_id}/dns_records",
                tok,
                payload,
            )
            out["action"] = "created"
            out["record_id"] = (created.get("result") or {}).get("id")
            out["success"] = bool(created.get("success"))
    except urllib.error.HTTPError as e:
        out["success"] = False
        out["http"] = e.code
        try:
            out["errors"] = json.loads(e.read().decode())
        except Exception:
            out["errors"] = [str(e)]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 3

    report = Path(os.environ.get("MKM_WORKSPACE_ROOT", r"C:\workspace")) / "reports" / "cloudflare_farm_jema_ai_dns_latest.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{out['action']}: {RECORD_NAME} -> {args.cname_target} success={out.get('success')}")
    print(f"report: {report}")
    return 0 if out.get("success") else 4


if __name__ == "__main__":
    raise SystemExit(main())
