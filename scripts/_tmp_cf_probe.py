#!/usr/bin/env python3
"""Probe Cloudflare API visibility (zones, accounts, registrar)."""
import json
import os
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for line in (root / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    if k.strip() in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and v.strip():
        os.environ.setdefault("CLOUDFLARE_API_TOKEN", v.strip().strip('"').strip("'"))

tok = os.environ.get("CLOUDFLARE_API_TOKEN", "")


def get(path: str) -> dict:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> None:
    print("=== token verify ===")
    try:
        v = get("/user/tokens/verify")
        print("verify:", v.get("success"), (v.get("result") or {}).get("status"))
    except Exception as e:
        print("verify failed:", e)

    print("\n=== accounts ===")
    try:
        a = get("/accounts?per_page=50")
        for ac in a.get("result") or []:
            print(ac.get("id"), ac.get("name"))
    except Exception as e:
        print("accounts failed:", e)

    print("\n=== all zones (any status) ===")
    page = 1
    names = []
    while page <= 5:
        z = get(f"/zones?per_page=50&page={page}")
        rows = z.get("result") or []
        if not rows:
            break
        for row in rows:
            names.append(row["name"])
            print(row["name"], row["id"], row.get("status"), row.get("account", {}).get("id"))
        if len(rows) < 50:
            break
        page += 1

    for apex in ("jema12.com", "mkmlife.com", "no1kmedi.com", "jema-ai.com"):
        print(f"\n=== zone?name={apex} ===")
        try:
            z = get(f"/zones?name={apex}")
            print("count", len(z.get("result") or []), "success", z.get("success"))
            for row in z.get("result") or []:
                print(" ", row.get("name"), row.get("id"), row.get("status"))
        except Exception as e:
            print("failed", e)

    print("\n=== registrar domains (account) ===")
    acct = "646e42cf881ab43043c32430e99d9af4"
    try:
        d = get(f"/accounts/{acct}/registrar/domains?per_page=50")
        for row in d.get("result") or []:
            print(row.get("name"), row.get("status"), row.get("id"))
    except Exception as e:
        print("registrar failed:", e)


if __name__ == "__main__":
    main()
