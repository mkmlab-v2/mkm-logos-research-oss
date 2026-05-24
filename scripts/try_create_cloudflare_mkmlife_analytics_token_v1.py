#!/usr/bin/env python3
"""Create mkmlife.com Zone Read + Analytics Read API token via parent CLOUDFLARE_API_TOKEN.

Parent may be jemaai-scoped; token creation only needs User API Tokens Write + permission group lookup.
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

OUT = ROOT / "reports" / "cloudflare_mkmlife_analytics_token_create_v1_latest.json"
SECRET = ROOT / "reports" / "cloudflare_mkmlife_analytics_token_secret_LOCAL.json"
MKMLIFE_ZONE_ID = "259a847ea3643566383972ebd3ede918"
NEEDED = ["Zone Read", "Analytics Read"]


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
            return exc.code, {"success": False, "errors": [{"message": str(exc), "code": exc.code}]}


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


def _apply_env(tok: str, token_id: str | None) -> None:
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    keys = {
        "MKM_MKMLIFE_CF_ANALYTICS_TOKEN": tok,
        "CLOUDFLARE_API_TOKEN": tok,
    }
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            out.append(line)
            continue
        k = line.split("=", 1)[0].strip()
        if k in keys:
            out.append(f"{k}={keys[k]}")
            seen.add(k)
        else:
            out.append(line)
    for k, v in keys.items():
        if k not in seen:
            out.append(f"{k}={v}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(
        json.dumps(
            {
                "schema": "cloudflare_mkmlife_analytics_token_secret_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "token_id": token_id,
                "MKM_MKMLIFE_CF_ANALYTICS_TOKEN": tok,
                "CLOUDFLARE_API_TOKEN": tok,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    tok, src = resolve_cloudflare_token()
    doc: dict = {
        "schema": "cloudflare_mkmlife_analytics_token_create_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parent_source": src,
        "parent_fp": token_fingerprint(tok) if tok else None,
        "zone": "mkmlife.com",
        "zone_id": MKMLIFE_ZONE_ID,
    }
    if not tok:
        doc["error"] = "no parent CLOUDFLARE_API_TOKEN"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        return 1

    groups = _permission_group_ids(tok, NEEDED)
    doc["permission_groups"] = groups
    missing = [n for n in NEEDED if n not in groups]
    if missing:
        doc["error"] = f"permission group lookup incomplete: {missing}"
        OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1

    rk = f"com.cloudflare.api.account.zone.{MKMLIFE_ZONE_ID}"
    policies = [
        {
            "effect": "allow",
            "permission_groups": [{"id": gid} for gid in groups.values()],
            "resources": {rk: "*"},
        }
    ]
    body = {
        "name": f"mkm-mkmlife-analytics-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
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
    if val:
        doc["new_token_fp"] = token_fingerprint(val)
        _apply_env(val, str(res.get("id") or ""))
        doc["secret_path"] = str(SECRET)
        doc["env_updated"] = True

    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "fp": doc.get("new_token_fp"), "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
