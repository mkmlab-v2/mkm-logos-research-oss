#!/usr/bin/env python3
"""Create mkmlife deploy token (Workers Scripts/KV + Zone Workers Routes) via parent CF token."""
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

OUT = ROOT / "reports" / "cloudflare_mkmlife_deploy_token_create_v1_latest.json"
SECRET = ROOT / "reports" / "cloudflare_mkmlife_deploy_token_secret_LOCAL.json"
MKMLIFE_ZONE_ID = "259a847ea3643566383972ebd3ede918"
ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"
ACCOUNT_GROUPS = ["Workers Scripts Edit", "Workers KV Storage Edit"]
ZONE_GROUPS = ["Zone Read", "Workers Routes Edit"]
USER_GROUPS = ["User Details Read"]


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
                "schema": "cloudflare_mkmlife_deploy_token_secret_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "token_id": token_id,
                "MKM_MKMLIFE_CF_DEPLOY_TOKEN": val,
                "CLOUDFLARE_API_TOKEN": val,
                "note": "Workers Scripts+KV (account) + Workers Routes+Zone Read (mkmlife.com zone)",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    tok, src = resolve_cloudflare_token(
        extra_keys=("MKM_CLOUDFLARE_PARENT_TOKEN", "MKM_CLOUDFLARE_TOKEN_ADMIN")
    )
    doc: dict = {
        "schema": "cloudflare_mkmlife_deploy_token_create_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_source": src,
        "parent_fp": token_fingerprint(tok) if tok else None,
        "zone": "mkmlife.com",
        "zone_id": MKMLIFE_ZONE_ID,
        "account_id": ACCOUNT_ID,
    }
    if not tok:
        doc["error"] = "no parent CLOUDFLARE_API_TOKEN"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 1

    needed = ACCOUNT_GROUPS + ZONE_GROUPS + USER_GROUPS
    groups = _permission_group_ids(tok, needed)
    doc["permission_groups"] = groups
    missing = [n for n in needed if n not in groups]
    if missing:
        doc["error"] = f"permission group lookup incomplete: {missing}"
        doc["preferred_fix"] = (
            "Dashboard: scripts/Open-MkmlifeCloudflareDeployTokenTemplate_v1.ps1 "
            "→ edit existing token OR create new → paste secret JSON → "
            "Invoke-ApplyMkmlifeCfDeployTokenFromSecret_v1.ps1"
        )
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1

    account_rk = f"com.cloudflare.api.account.{ACCOUNT_ID}"
    zone_rk = f"com.cloudflare.api.account.zone.{MKMLIFE_ZONE_ID}"
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
        {
            "effect": "allow",
            "permission_groups": [{"id": groups[n]} for n in USER_GROUPS],
            "resources": {"com.cloudflare.api.user.*": "*"},
        },
    ]
    body = {
        "name": f"mkm-mkmlife-deploy-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
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
    doc["new_token_id"] = res.get("id")
    doc["new_token_name"] = res.get("name")
    if not val:
        doc["error"] = "create ok but no token value"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 1

    doc["new_token_fp"] = token_fingerprint(val)
    _apply_secret(val, str(res.get("id") or ""))
    doc["secret_path"] = str(SECRET)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "secret_path": str(SECRET), "fp": doc["new_token_fp"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
