#!/usr/bin/env python3
"""Solo-dev: create CF API token (DNS + Zone WAF Edit + Cache Rules Edit) for jemaai.cloud via parent token.

Requires parent CLOUDFLARE_API_TOKEN with User API Tokens Write + zone visibility.

  py scripts/try_create_cloudflare_jemaai_solo_edge_token_v1.py
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
from mkm_cloudflare_token_v1 import resolve_cloudflare_token, token_fingerprint  # noqa: E402

OUT = ROOT / "reports" / "cloudflare_jemaai_solo_edge_token_create_v1_latest.json"
SECRET = ROOT / "reports" / "cloudflare_jemaai_solo_edge_token_secret_LOCAL.json"
JEMAAI_ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
NEEDED = ["Zone Read", "DNS Read", "DNS Edit", "Zone WAF Edit", "Cache Rules Edit"]


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
        "schema": "cloudflare_jemaai_solo_edge_token_create_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_source": src,
        "parent_fp": token_fingerprint(tok) if tok else None,
        "zone": "jemaai.cloud",
        "zone_id": JEMAAI_ZONE_ID,
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
            "likely_cause": "CLOUDFLARE_API_TOKEN lacks User API Tokens Write (GET /user/tokens/permission-groups often 400/403)",
            "preferred_fix": (
                "Edit the EXISTING token in CF dashboard: add Zone Read + Zone WAF Edit + "
                "Cache Rules Edit on jemaai.cloud only (see JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md). "
                "Do NOT rotate CLOUDFLARE_API_TOKEN daily."
            ),
            "alternate_fix": (
                "Create custom token in UI → reports/cloudflare_jemaai_solo_edge_token_secret_LOCAL.json "
                "→ Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1"
            ),
        }
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return 1

    rk = f"com.cloudflare.api.account.zone.{JEMAAI_ZONE_ID}"
    policies = [
        {
            "effect": "allow",
            "permission_groups": [{"id": gid} for gid in groups.values()],
            "resources": {rk: "*"},
        }
    ]
    body = {
        "name": f"mkm-jemaai-solo-edge-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
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
        "schema": "cloudflare_jemaai_solo_edge_token_secret_v1",
        "generated_at_utc": doc["generated_at_utc"],
        "token_id": (pl.get("result") or {}).get("id"),
        "CLOUDFLARE_RULESETS_API_TOKEN": val,
        "CLOUDFLARE_API_TOKEN": val,
    }
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(json.dumps(secret, indent=2), encoding="utf-8")
    doc["secret_path"] = str(SECRET)
    doc["new_token_fp"] = token_fingerprint(val)
    doc["solo_dev_hint"] = (
        "Run scripts/Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1 "
        "(sets CLOUDFLARE_RULESETS_API_TOKEN only — never overwrites CLOUDFLARE_API_TOKEN)"
    )

    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "secret_path": str(SECRET), "fp": doc["new_token_fp"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
