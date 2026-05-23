#!/usr/bin/env python3
"""Create CF API token for jema-ai.com dynamic redirect (Zone Read + Zone Rulesets).

Parent CLOUDFLARE_API_TOKEN needs User API Tokens Write. If lookup fails, use dashboard
edit on existing CLOUDFLARE_RULESETS_API_TOKEN (add jema-ai.com zone) — see triage jema_ai_redirect_guard.

  py scripts/try_create_cloudflare_jema_ai_redirect_token_v1.py
"""
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
from mkm_cloudflare_token_v1 import (  # noqa: E402
    JEMA_AI_ZONE_ID,
    resolve_cloudflare_token,
    token_fingerprint,
)

OUT = ROOT / "reports" / "cloudflare_jema_ai_redirect_token_create_v1_latest.json"
SECRET = ROOT / "reports" / "cloudflare_jema_ai_redirect_token_secret_LOCAL.json"
# CF permission group names (search UI: "Rulesets" / "Zone Read")
NEEDED = ["Zone Read", "Zone Rulesets"]


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


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


def main() -> int:
    tok, src = resolve_cloudflare_token()
    doc: dict = {
        "schema": "cloudflare_jema_ai_redirect_token_create_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_source": src,
        "parent_fp": token_fingerprint(tok) if tok else None,
        "zone": "jema-ai.com",
        "zone_id": JEMA_AI_ZONE_ID,
    }
    if not tok:
        doc["error"] = "no parent CLOUDFLARE_API_TOKEN"
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return 1

    groups = _permission_group_ids(tok, NEEDED)
    doc["permission_groups"] = groups
    missing = [n for n in NEEDED if n not in groups]
    if missing:
        doc["error"] = f"permission group lookup incomplete: {missing}"
        doc["recurrence_guard"] = {
            "parent_cannot_create_child_tokens": True,
            "preferred_fix": (
                "CF dashboard → edit CLOUDFLARE_RULESETS_API_TOKEN (cfut_5…) → add jema-ai.com "
                "+ Zone Read + Zone Rulesets. Do NOT rotate CLOUDFLARE_API_TOKEN."
            ),
            "alternate_fix": (
                "Custom token in UI → reports/cloudflare_jema_ai_redirect_token_secret_LOCAL.json "
                "→ Invoke-ApplyJemaAiRedirectTokenFromSecret_v1.ps1"
            ),
        }
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return 1

    rk = f"com.cloudflare.api.account.zone.{JEMA_AI_ZONE_ID}"
    policies = [
        {
            "effect": "allow",
            "permission_groups": [{"id": gid} for gid in groups.values()],
            "resources": {rk: "*"},
        }
    ]
    body = {
        "name": f"mkm-jema-ai-redirect-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "policies": policies,
    }
    st, pl = _api(tok, "POST", "/user/tokens", body)
    doc["create_http"] = st
    doc["create_success"] = bool(pl.get("success"))
    doc["create_errors"] = pl.get("errors")
    if not pl.get("success"):
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(json.dumps(doc, indent=2))
        return 1

    val = ((pl.get("result") or {}).get("value") or "").strip()
    if not val:
        doc["error"] = "create ok but no token value in response"
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return 1

    secret = {
        "schema": "cloudflare_jema_ai_redirect_token_secret_v1",
        "generated_at_utc": doc["generated_at_utc"],
        "token_id": (pl.get("result") or {}).get("id"),
        "MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN": val,
    }
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(json.dumps(secret, indent=2), encoding="utf-8")
    doc["secret_path"] = str(SECRET)
    doc["new_token_fp"] = token_fingerprint(val)
    doc["next"] = "powershell -File scripts/Invoke-ApplyJemaAiRedirectTokenFromSecret_v1.ps1"

    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "secret_path": str(SECRET), "fp": doc["new_token_fp"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
