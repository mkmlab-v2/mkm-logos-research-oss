#!/usr/bin/env python3
"""Operator pack when mkmlab.space CF zone stays pending — facts only, no secrets."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ensure_mkmlab_space_cloudflare_dns_v1 import _api  # noqa: E402
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

OUT_JSON = ROOT / "reports" / "mkmlab_cloudflare_pending_operator_latest.json"
OUT_MD = ROOT / "reports" / "mkmlab_cloudflare_pending_operator_latest.md"
ZONE_ID = "38a47f29983bd4ebce3798be08f59ba3"
DASHBOARD = f"https://dash.cloudflare.com/?to=/:account/{ZONE_ID}/mkmlab.space"


def _try(method: str, url: str, token: str, body: dict | None = None) -> dict:
    try:
        j = _api(method, url, token, body)
        return {"ok": True, "success": bool(j.get("success"))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:240]}


def main() -> int:
    token, src = resolve_cloudflare_token()
    pack: dict = {
        "schema": "mkmlab_cloudflare_pending_operator_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "apex": "mkmlab.space",
        "zone_id": ZONE_ID,
        "token_source": src,
        "token_present": bool(token),
        "dashboard_url": DASHBOARD,
        "site_live": None,
        "zone": {},
        "api_permissions_probe": {},
        "next_actions": [],
    }
    ready = ROOT / "reports" / "mkmlab_space_readiness_latest.json"
    if ready.is_file():
        r = json.loads(ready.read_text(encoding="utf-8"))
        pack["site_live"] = r.get("http_all_ok")

    if not token:
        pack["next_actions"] = ["Set CLOUDFLARE_API_TOKEN in .env and User env"]
        OUT_JSON.write_text(json.dumps(pack, indent=2), encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT_JSON)}))
        return 2

    j = _api("GET", f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}", token)
    zr = j.get("result") or {}
    pack["zone"] = {
        "status": zr.get("status"),
        "name_servers": zr.get("name_servers"),
        "original_name_servers": zr.get("original_name_servers"),
        "original_registrar": zr.get("original_registrar"),
        "activated_on": zr.get("activated_on"),
    }
    zid = ZONE_ID
    pack["api_permissions_probe"] = {
        "activation_check_put": _try(
            "PUT",
            f"https://api.cloudflare.com/client/v4/zones/{zid}/activation_check",
            token,
        ),
        "ssl_settings_patch": _try(
            "PATCH",
            f"https://api.cloudflare.com/client/v4/zones/{zid}/settings/ssl",
            token,
            body={"value": "full"},
        ),
    }

    status = pack["zone"].get("status")
    act_ok = pack["api_permissions_probe"]["activation_check_put"].get("ok")
    if status == "active":
        pack["next_actions"] = [
            "Run: py scripts/finalize_mkmlab_cloudflare_zone_v1.py",
        ]
    elif not act_ok:
        pack["next_actions"] = [
            "Cloudflare Dashboard → mkmlab.space → Overview → Check nameservers / Complete setup",
            f"Dashboard: {DASHBOARD}",
            "Optional: create API token with Zone Edit + Zone Settings Edit (all zones or mkmlab only), "
            "update .env CLOUDFLARE_API_TOKEN, then sync User env and re-run finalize",
            "Public HTTPS already OK via VPS Let's Encrypt until zone is active",
        ]
    else:
        pack["next_actions"] = [
            "Re-run: py scripts/finalize_mkmlab_cloudflare_zone_v1.py --polls 12 --sleep-s 45",
        ]

    OUT_JSON.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    lines = [
        "# mkmlab.space — Cloudflare pending operator pack",
        "",
        f"- Generated: {pack['generated_at_utc']}",
        f"- Zone status: **{pack['zone'].get('status')}**",
        f"- Site probe http_all_ok: **{pack.get('site_live')}**",
        f"- CF name_servers: {', '.join(pack['zone'].get('name_servers') or [])}",
        f"- CF original_name_servers (stale until active): {', '.join(pack['zone'].get('original_name_servers') or [])}",
        "",
        "## Next actions",
        "",
    ]
    for i, a in enumerate(pack["next_actions"], 1):
        lines.append(f"{i}. {a}")
    lines.extend(["", f"[Open Cloudflare zone]({DASHBOARD})", ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": True, "zone_status": status, "out_json": str(OUT_JSON), "out_md": str(OUT_MD)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
