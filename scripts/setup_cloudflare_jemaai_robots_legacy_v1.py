#!/usr/bin/env python3
"""jemaai.cloud: disable CF managed robots.txt prepending; serve origin Disallow /legacy/."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
ZONE_NAME = "jemaai.cloud"
OUT = ROOT / "reports" / "cloudflare_jemaai_robots_legacy_v1_latest.json"
ROBOTS_URL = f"https://{ZONE_NAME}/robots.txt"
LEGACY_DISALLOW = "Disallow: /legacy/"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_dotenv_token() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    rulesets_tok = ""
    fallback_tok = ""
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if not val:
            continue
        if key == "CLOUDFLARE_RULESETS_API_TOKEN":
            rulesets_tok = val
        elif key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and not fallback_tok:
            fallback_tok = val
    if rulesets_tok:
        os.environ.setdefault("CLOUDFLARE_RULESETS_API_TOKEN", rulesets_tok)
        os.environ.setdefault("CLOUDFLARE_API_TOKEN", rulesets_tok)
    elif fallback_tok:
        os.environ.setdefault("CLOUDFLARE_API_TOKEN", fallback_tok)


def _api(tok: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"success": False, "errors": [{"message": str(e)}]}
        return e.code, payload


def _fetch_robots() -> dict[str, Any]:
    # Bot Fight may 403 default Python UA; crawlers use explicit bot UA.
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
    try:
        req = urllib.request.Request(ROBOTS_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        return {
            "http": resp.status,
            "legacy_disallow": LEGACY_DISALLOW in body,
            "managed_cf_header": "Content-Signal" in body or "Cloudflare Managed Content" in body,
            "body_tail": body[-400:] if len(body) > 400 else body,
            "probe_ua": "Googlebot",
        }
    except Exception as exc:
        return {"http": 0, "error": str(exc), "legacy_disallow": False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-cf", action="store_true", help="Only probe robots.txt (no API write)")
    args = ap.parse_args()

    _load_dotenv_token()
    tok = (
        os.environ.get("CLOUDFLARE_RULESETS_API_TOKEN", "").strip()
        or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )

    doc: dict[str, Any] = {
        "schema": "cloudflare_jemaai_robots_legacy_v1",
        "generated_at_utc": _utc_now(),
        "zone": ZONE_NAME,
        "zone_id": ZONE_ID,
        "robots_url": ROBOTS_URL,
        "origin_nginx_snippet": "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/nginx_snippets/jemaai_showroom_legacy_noindex_v1.conf",
        "before": _fetch_robots(),
    }

    if not tok:
        doc["cf"] = {"ok": False, "reason": "CLOUDFLARE_API_TOKEN missing"}
        doc["after"] = doc["before"]
        doc["manual_dashboard"] = (
            "dash.cloudflare.com → jemaai.cloud → Security → Bots → "
            "disable managed robots.txt / Content Signals; then origin serves Disallow: /legacy/"
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "reason": "token_missing", "out": str(OUT)}, ensure_ascii=False))
        return 1

    if not args.skip_cf:
        get_code, get_payload = _api(tok, "GET", f"/zones/{ZONE_ID}/bot_management")
        doc["cf_get"] = {"http": get_code, "success": get_payload.get("success"), "result": get_payload.get("result")}
        if get_code != 200 or not get_payload.get("success"):
            doc["cf"] = {"ok": False, "reason": "bot_management_get_failed", "errors": get_payload.get("errors")}
            doc["origin_fix"] = {
                "reason": "CF prepends origin only when :80 returns HTTP 200 for /robots.txt",
                "script": "powershell -File scripts\\Invoke-JemaaiRobotsTxtOriginVps_v1.ps1",
                "automation": "powershell -File scripts\\Invoke-JemaaiRobotsLegacyAutomation_v1.ps1",
            }
        else:
            current = get_payload.get("result") or {}
            desired = dict(current)
            desired["is_robots_txt_managed"] = False
            desired["cf_robots_variant"] = "off"
            doc["cf_desired"] = {
                "is_robots_txt_managed": False,
                "cf_robots_variant": "off",
            }
            if args.dry_run:
                doc["cf"] = {"ok": True, "dry_run": True}
            else:
                put_code, put_payload = _api(tok, "PUT", f"/zones/{ZONE_ID}/bot_management", desired)
                doc["cf_put"] = {"http": put_code, "success": put_payload.get("success"), "errors": put_payload.get("errors")}
                doc["cf"] = {"ok": put_code == 200 and bool(put_payload.get("success"))}

    doc["after"] = _fetch_robots()
    doc["verify"] = {
        "legacy_disallow_present": doc["after"].get("legacy_disallow"),
        "managed_cf_still_present": doc["after"].get("managed_cf_header"),
    }
    doc["repro"] = "py scripts/setup_cloudflare_jemaai_robots_legacy_v1.py"
    doc["nginx_redeploy"] = "powershell -File scripts\\Invoke-JemaaiShowroomObserveCanonicalCleanup_v1.ps1"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = bool(doc.get("verify", {}).get("legacy_disallow_present"))
    print(json.dumps({"ok": ok, "out": str(OUT), "verify": doc["verify"]}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
