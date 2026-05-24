#!/usr/bin/env python3
"""Try POST /user/tokens for Zone DNS Read+Edit (needs parent token with API Tokens Write)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token, token_fingerprint  # noqa: E402

OUT = ROOT / "reports" / "cloudflare_dns_token_create_attempt_latest.json"
ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"
ZONE_NAMES = (
    "mkmlab.space",
    "jemaai.cloud",
    "jema-ai.com",
    "no1kmedi.com",
    "mkmlife.com",
    "jema12.com",
)


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"success": False, "errors": [{"message": raw[:500]}]}


def _permission_group_ids(tok: str, names: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in names:
        q = urllib.parse.urlencode({"name": name})
        _, pl = _api(tok, "GET", f"/user/tokens/permission-groups?{q}")
        for g in pl.get("result") or []:
            gn = (g.get("name") or "").strip()
            if gn in names and gn not in found:
                found[gn] = str(g["id"])
    return found


def _zone_resource_keys(tok: str) -> dict[str, str]:
    """zone_id -> zone_name for target zones."""
    keys: dict[str, str] = {}
    page = 1
    while True:
        _, pl = _api(tok, "GET", f"/zones?per_page=50&page={page}")
        for z in pl.get("result") or []:
            n = (z.get("name") or "").lower()
            if n in {x.lower() for x in ZONE_NAMES}:
                keys[f"com.cloudflare.api.account.zone.{z['id']}"] = n
        total = (pl.get("result_info") or {}).get("total_pages", 1)
        if page >= total:
            break
        page += 1
    return keys


def main() -> int:
    tok, src = resolve_cloudflare_token()
    doc: dict = {
        "schema": "cloudflare_dns_token_create_attempt_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_token_source": src,
        "parent_token_fp": token_fingerprint(tok) if tok else None,
        "steps": [],
    }
    if not tok:
        doc["error"] = "no parent token"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 2

    needed = ["Zone Read", "DNS Read", "DNS Edit"]
    groups = _permission_group_ids(tok, needed)
    doc["permission_groups"] = groups
    doc["steps"].append({"step": "lookup_permission_groups", "found": list(groups.keys())})

    missing = [n for n in needed if n not in groups]
    if missing:
        doc["error"] = f"permission group lookup incomplete: {missing}"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1

    zone_keys = _zone_resource_keys(tok)
    doc["zone_resources"] = zone_keys
    if not zone_keys:
        doc["error"] = "no target zones visible to parent token"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 1

    resources: dict[str, str] = {}
    for rk in zone_keys:
        resources[rk] = "*"

    policies = [
        {
            "effect": "allow",
            "permission_groups": [{"id": groups["Zone Read"]}, {"id": groups["DNS Read"]}, {"id": groups["DNS Edit"]}],
            "resources": resources,
        }
    ]
    body = {
        "name": f"mkm-dns-automation-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "policies": policies,
    }
    st, pl = _api(tok, "POST", "/user/tokens", body)
    doc["create_http"] = st
    doc["create_success"] = pl.get("success")
    doc["create_errors"] = pl.get("errors")
    if pl.get("success") and pl.get("result"):
        res = pl["result"]
        doc["new_token_id"] = res.get("id")
        doc["new_token_name"] = res.get("name")
        val = (res.get("value") or "").strip()
        if val:
            doc["new_token_fp"] = token_fingerprint(val)
            doc["write_hint"] = (
                "Add to .env CLOUDFLARE_API_TOKEN= then sync_required_env_to_user.ps1. "
                "Token value stored ONLY in reports/cloudflare_dns_token_create_secret_LOCAL.json (gitignored path)."
            )
            secret_path = ROOT / "reports" / "cloudflare_dns_token_create_secret_LOCAL.json"
            secret_path.write_text(
                json.dumps(
                    {
                        "schema": "cloudflare_dns_token_secret_v1",
                        "generated_at_utc": doc["generated_at_utc"],
                        "token_id": res.get("id"),
                        "CLOUDFLARE_API_TOKEN": val,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            doc["secret_path"] = str(secret_path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": bool(pl.get("success")), "http": st, "out": str(OUT)}, ensure_ascii=False))
    return 0 if pl.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
