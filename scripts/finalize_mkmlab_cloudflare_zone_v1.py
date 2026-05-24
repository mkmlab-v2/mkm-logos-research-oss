"""Poll mkmlab.space Cloudflare zone activation; apply edge settings when active."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ensure_mkmlab_space_cloudflare_dns_v1 import _api, _zone_id  # noqa: E402
from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

OUT = ROOT / "reports" / "mkmlab_cloudflare_zone_finalize_latest.json"
ZONE_ID_DEFAULT = "38a47f29983bd4ebce3798be08f59ba3"
SETTINGS = (
    ("ssl", "full"),
    ("always_use_https", "on"),
    ("automatic_https_rewrites", "on"),
    ("min_tls_version", "1.2"),
)


def _patch_setting(token: str, zid: str, setting_id: str, value: str) -> dict:
    url = f"https://api.cloudflare.com/client/v4/zones/{zid}/settings/{setting_id}"
    try:
        j = _api("PATCH", url, token, {"value": value})
        return {"setting": setting_id, "value": value, "ok": bool(j.get("success"))}
    except Exception as exc:
        return {"setting": setting_id, "value": value, "ok": False, "error": str(exc)}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--zone-id", default=ZONE_ID_DEFAULT)
    ap.add_argument("--polls", type=int, default=6, help="activation polls (interval --sleep-s)")
    ap.add_argument("--sleep-s", type=int, default=30)
    args = ap.parse_args()

    token, src = resolve_cloudflare_token()
    report: dict = {
        "schema": "mkmlab_cloudflare_zone_finalize_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "token_source": src,
        "zone_id": args.zone_id,
        "polls": [],
        "settings": [],
        "ok": False,
    }
    if not token:
        report["error"] = "no CLOUDFLARE_API_TOKEN"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(OUT)}))
        return 2

    zid = _zone_id(token, args.zone_id)
    report["zone_id"] = zid
    status = "pending"
    for i in range(max(1, args.polls)):
        j = _api("GET", f"https://api.cloudflare.com/client/v4/zones/{zid}", token)
        status = (j.get("result") or {}).get("status", "unknown")
        report["polls"].append({"n": i + 1, "status": status})
        if status == "active":
            break
        if i + 1 < args.polls:
            time.sleep(max(5, args.sleep_s))

    j_zone = _api("GET", f"https://api.cloudflare.com/client/v4/zones/{zid}", token)
    zr = j_zone.get("result") or {}
    report["zone_meta"] = {
        "name_servers": zr.get("name_servers"),
        "original_name_servers": zr.get("original_name_servers"),
        "original_registrar": zr.get("original_registrar"),
        "activated_on": zr.get("activated_on"),
    }
    report["zone_status"] = status
    try:
        _api(
            "PUT",
            f"https://api.cloudflare.com/client/v4/zones/{zid}/activation_check",
            token,
            {},
        )
        report["activation_check"] = "requested"
        j2 = _api("GET", f"https://api.cloudflare.com/client/v4/zones/{zid}", token)
        status = (j2.get("result") or {}).get("status", status)
        report["zone_status"] = status
        report["zone_meta"]["after_activation_check"] = (j2.get("result") or {}).get("status")
    except Exception as exc:
        report["activation_check"] = f"skipped:{exc}"

    if status == "active":
        for sid, val in SETTINGS:
            report["settings"].append(_patch_setting(token, zid, sid, val))
        report["ok"] = all(s.get("ok") for s in report["settings"]) if report["settings"] else True
    else:
        report["ok"] = status in ("active", "pending")
        report["note"] = (
            "zone still pending; origin TLS on VPS is serving https. "
            "Re-run later or check Cloudflare dashboard Overview."
        )

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "zone_status": status, "out": str(OUT)}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
