#!/usr/bin/env python3
"""O-P5 bridge: jema-ai.com /studio* -> jemaai.cloud Oracle v5 (zone visible to API token).

Use when jema12.com/studio already 301s to jema-ai.com/studio (CF zone jema12 not in token).
Prepends rule on jema-ai.com dynamic redirect entrypoint.

  py scripts/setup_cloudflare_jema_ai_studio_oracle_bridge_v1.py --dry-run
  py scripts/setup_cloudflare_jema_ai_studio_oracle_bridge_v1.py
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
DEFAULT_OUT = ROOT / "reports" / "cloudflare_jema_ai_studio_oracle_bridge_latest.json"
DEFAULT_ZONE_ID = "e64f17593ce48e31c2839b421c8bd4c0"
TARGET_URL = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"
STUDIO_EXPR = (
    '(http.request.uri.path eq "/studio") or '
    '(http.request.uri.path eq "/studio/") or '
    'starts_with(http.request.uri.path, "/studio/")'
)
DESC = "jema-ai.com /studio -> jemaai.cloud oracle v5 (O-P5 bridge)"


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


def _bridge_rule() -> dict:
    return {
        "action": "redirect",
        "expression": STUDIO_EXPR,
        "description": DESC,
        "action_parameters": {
            "from_value": {
                "status_code": 302,
                "target_url": {"value": TARGET_URL},
                "preserve_query_string": True,
            }
        },
    }


def main() -> int:
    _load_dotenv_token()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zone-id", default=DEFAULT_ZONE_ID)
    ap.add_argument("--target-url", default=TARGET_URL)
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
    merged = [_bridge_rule()] + filtered

    out = {
        "schema": "cloudflare_jema_ai_studio_oracle_bridge_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zone_id": zid,
        "host": "jema-ai.com",
        "target_url": args.target_url,
        "dry_run": args.dry_run,
        "rule_count_before": len(existing),
        "rule_count_after": len(merged),
    }

    if args.dry_run:
        out["action"] = "dry_run"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DRY-RUN ok zone={zid} jema-ai.com /studio -> {args.target_url}")
        return 0

    st, pl = _api(tok, "PUT", ep, {"rules": merged})
    out["put"] = {"http": st, "success": pl.get("success"), "errors": pl.get("errors")}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not pl.get("success"):
        print("PUT failed", pl.get("errors"), file=sys.stderr)
        return 3
    print(f"OK: jema-ai.com /studio bridge -> {args.target_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
