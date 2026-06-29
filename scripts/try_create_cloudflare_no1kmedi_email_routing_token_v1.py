#!/usr/bin/env python3
"""Create no1kmedi Email Routing token via parent CF token (API), then apply setup."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import resolve_cloudflare_token, token_fingerprint  # noqa: E402

OUT = ROOT / "reports" / "cloudflare_no1kmedi_email_routing_token_create_v1_latest.json"
SECRET = ROOT / "reports" / "cloudflare_no1kmedi_email_routing_token_secret_LOCAL.json"
NO1K_ZONE_ID = "1516522160411707c33f84e145416a53"
ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"
ACCOUNT_GROUPS = ["Email Routing Addresses Edit"]
ZONE_GROUPS = ["Email Routing Rules Edit", "Zone Read"]


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}", data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode())
        except Exception:
            return exc.code, {"success": False, "errors": [{"message": str(exc)}]}


def _permission_group_ids(tok: str, names: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in names:
        q = urllib.parse.urlencode({"name": name})
        _, pl = _api(tok, "GET", f"/user/tokens/permission-groups?{q}")
        for g in pl.get("result") or []:
            gn = (g.get("name") or "").strip()
            if gn == name and gn not in found:
                found[gn] = str(g["id"])
    return found


def _apply_secret(val: str, token_id: str | None) -> None:
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(
        json.dumps(
            {
                "schema": "cloudflare_no1kmedi_email_routing_token_secret_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "token_id": token_id,
                "MKM_NO1KMEDI_EMAIL_ROUTING_TOKEN": val,
                "note": "Account Email Routing Addresses Edit + Zone Email Routing Rules Edit + Zone Read (no1kmedi.com)",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    tok, src = resolve_cloudflare_token(
        extra_keys=(
            "MKM_CLOUDFLARE_PARENT_TOKEN",
            "MKM_CLOUDFLARE_TOKEN_ADMIN",
            "MKM_NO1KMEDI_EMAIL_ROUTING_TOKEN",
        )
    )
    doc: dict = {
        "schema": "cloudflare_no1kmedi_email_routing_token_create_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_source": src,
        "parent_fp": token_fingerprint(tok) if tok else None,
        "zone": "no1kmedi.com",
        "zone_id": NO1K_ZONE_ID,
        "account_id": ACCOUNT_ID,
    }
    if not tok:
        doc["error"] = "no parent token"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 1

    # Already has email routing?
    st, pl = _api(tok, "GET", f"/zones/{NO1K_ZONE_ID}/email/routing")
    if pl.get("success"):
        doc["existing_token_has_email_routing"] = True
        _apply_secret(tok, None)
        doc["secret_path"] = str(SECRET)
        doc["note"] = "Reused token that already passes email/routing GET"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "reused": True, "secret_path": str(SECRET)}, ensure_ascii=False))
        return 0

    needed = ACCOUNT_GROUPS + ZONE_GROUPS
    groups = _permission_group_ids(tok, needed)
    doc["permission_groups"] = groups
    missing = [n for n in needed if n not in groups]
    if missing:
        doc["error"] = f"permission group lookup incomplete: {missing}"
        doc["ui_fallback"] = "scripts/Open-No1kmediEmailRoutingTokenTemplate_v1.ps1"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1

    account_rk = f"com.cloudflare.api.account.{ACCOUNT_ID}"
    zone_rk = f"com.cloudflare.api.account.zone.{NO1K_ZONE_ID}"
    policies = [
        {
            "effect": "allow",
            "permission_groups": [{"id": groups[n]} for n in ACCOUNT_GROUPS],
            "resources": {account_rk: "*"},
        },
        {
            "effect": "allow",
            "permission_groups": [{"id": groups[n]} for n in ZONE_GROUPS],
            "resources": {zone_rk: "*"},
        },
    ]
    body = {
        "name": f"mkm-no1kmedi-email-routing-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "policies": policies,
    }
    st, pl = _api(tok, "POST", "/user/tokens", body)
    doc["create_http"] = st
    doc["create_success"] = bool(pl.get("success"))
    doc["create_errors"] = pl.get("errors")
    if not pl.get("success"):
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "errors": pl.get("errors")}, ensure_ascii=False))
        return 1

    res = pl.get("result") or {}
    val = (res.get("value") or "").strip()
    if not val:
        doc["error"] = "create ok but no token value"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 1

    doc["new_token_id"] = res.get("id")
    doc["new_token_fp"] = token_fingerprint(val)
    _apply_secret(val, str(res.get("id") or ""))
    doc["secret_path"] = str(SECRET)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "secret_path": str(SECRET)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
