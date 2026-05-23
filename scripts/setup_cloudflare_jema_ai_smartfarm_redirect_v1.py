#!/usr/bin/env python3
"""jema-ai.com /smartfarm* -> farm.jema-ai.com (308) via Cloudflare dynamic redirect.

Prepends path-specific rule ahead of apex-wide jema-ai.com -> app.jema-ai.com rules.
SSOT nginx fallback: scripts/deploy/linux/apply_jema_ai_com_apex_nginx_v1.sh

  py scripts/setup_cloudflare_jema_ai_smartfarm_redirect_v1.py --dry-run
  py scripts/setup_cloudflare_jema_ai_smartfarm_redirect_v1.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "cloudflare_jema_ai_smartfarm_redirect_latest.json"
DEFAULT_ZONE_ID = "e64f17593ce48e31c2839b421c8bd4c0"
SMARTFARM_EXPR = (
    '(http.request.uri.path eq "/smartfarm") or '
    '(http.request.uri.path eq "/smartfarm/") or '
    'starts_with(http.request.uri.path, "/smartfarm/")'
)
DESC = "jema-ai.com /smartfarm -> farm.jema-ai.com (308 B2B canonical)"
TARGET_EXPR = (
    'concat("https://farm.jema-ai.com", '
    'if(eq(http.request.uri.path, "/smartfarm") or eq(http.request.uri.path, "/smartfarm/"), '
    '"/", regex_replace(http.request.uri.path, "^/smartfarm", "")))'
)


def _load_dotenv_token() -> None:
    dotenv = ROOT / ".env"
    if not dotenv.is_file():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key in ("CLOUDFLARE_API_TOKEN", "CF_API_TOKEN") and val:
            os.environ.setdefault("CLOUDFLARE_API_TOKEN", val)
            break


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    data = None
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
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


def _smartfarm_rule() -> dict:
    return {
        "action": "redirect",
        "expression": SMARTFARM_EXPR,
        "description": DESC,
        "action_parameters": {
            "from_value": {
                "status_code": 308,
                "target_url": {"expression": TARGET_EXPR},
                "preserve_query_string": True,
            }
        },
    }


def main() -> int:
    _load_dotenv_token()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zone-id", default=DEFAULT_ZONE_ID)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip() or os.environ.get("CF_API_TOKEN", "").strip()
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    zid = args.zone_id.strip()
    ep = f"/zones/{zid}/rulesets/phases/http_request_dynamic_redirect/entrypoint"
    _, cur = _api(tok, "GET", ep)
    existing = list((cur.get("result") or {}).get("rules") or []) if cur.get("success") else []
    filtered = [r for r in existing if DESC not in (r.get("description") or "")]
    merged = [_smartfarm_rule()] + filtered

    out = {
        "schema": "cloudflare_jema_ai_smartfarm_redirect_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zone_id": zid,
        "host": "jema-ai.com",
        "target_host": "farm.jema-ai.com",
        "status_code": 308,
        "dry_run": args.dry_run,
        "rule_count_before": len(existing),
        "rule_count_after": len(merged),
    }

    if args.dry_run:
        out["action"] = "dry_run"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DRY-RUN ok zone={zid} jema-ai.com /smartfarm -> farm.jema-ai.com (308)")
        return 0

    st, pl = _api(tok, "PUT", ep, {"rules": merged})
    out["put"] = {"http": st, "success": pl.get("success"), "errors": pl.get("errors")}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not pl.get("success"):
        print("PUT failed", pl.get("errors"), file=sys.stderr)
        return 3
    print("OK: jema-ai.com /smartfarm -> farm.jema-ai.com (308)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
