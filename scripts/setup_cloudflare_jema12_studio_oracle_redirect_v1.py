#!/usr/bin/env python3
"""O-P5 alt: jema12.com /studio → jemaai.cloud Oracle v5 via Cloudflare dynamic redirect.

Prepends a path-specific rule ahead of existing redirect rules (GET entrypoint, merge, PUT).
Does not change apex-wide rules except by adding a higher-priority /studio rule.

  py scripts/setup_cloudflare_jema12_studio_oracle_redirect_v1.py --dry-run
  py scripts/setup_cloudflare_jema12_studio_oracle_redirect_v1.py --zone-id <id>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "cloudflare_jema12_studio_oracle_redirect_latest.json"
TARGET_URL = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"
STUDIO_PATH_EXPR = (
    '(http.request.uri.path eq "/studio") or '
    '(http.request.uri.path eq "/studio/") or '
    'starts_with(http.request.uri.path, "/studio/")'
)
# www hits a separate apex-wide rule → jema-ai.com unless this is ranked first.
WWW_STUDIO_EXPR = f'(http.host eq "www.jema12.com") and ({STUDIO_PATH_EXPR})'
APEX_STUDIO_EXPR = (
    '(http.host eq "jema12.com") and '
    f"({STUDIO_PATH_EXPR})"
)


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


def _zone_lookup(tok: str, apex: str) -> dict[str, Any] | None:
    enc = urllib.parse.quote(apex, safe="")
    _, payload = _api(tok, "GET", f"/zones?name={enc}&status=active")
    if not payload.get("success"):
        return None
    for z in payload.get("result") or []:
        if (z.get("name") or "").lower() == apex.lower():
            return z
    return None


def _redirect_rule(expression: str, description: str, *, status_code: int = 301) -> dict[str, Any]:
    return {
        "action": "redirect",
        "expression": expression,
        "description": description,
        "action_parameters": {
            "from_value": {
                "status_code": status_code,
                "target_url": {"value": TARGET_URL},
                "preserve_query_string": True,
            }
        },
    }


def _www_studio_rule() -> dict[str, Any]:
    return _redirect_rule(
        WWW_STUDIO_EXPR,
        "jema12 www /studio -> jemaai.cloud oracle v6 (O-P5)",
    )


def _apex_studio_rule() -> dict[str, Any]:
    return _redirect_rule(
        APEX_STUDIO_EXPR,
        "jema12 apex /studio -> jemaai.cloud oracle v6 (O-P5)",
    )


def main() -> int:
    _load_dotenv_token()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apex", default="jema12.com")
    ap.add_argument("--zone-id", default="")
    ap.add_argument("--target-url", default=TARGET_URL)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tok = (
        os.environ.get("CLOUDFLARE_RULESETS_API_TOKEN", "").strip()
        or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    out: dict[str, Any] = {
        "schema": "cloudflare_jema12_studio_oracle_redirect_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "apex": args.apex,
        "target_url": args.target_url,
        "dry_run": args.dry_run,
        "steps": [],
    }

    zone: dict[str, Any] | None = None
    zid_cli = args.zone_id.strip()
    if zid_cli:
        _, pl = _api(tok, "GET", f"/zones/{zid_cli}")
        if pl.get("success") and pl.get("result"):
            zone = pl["result"]
        else:
            # Zone list may work while GET /zones/{id} is denied; trust CLI id (O-P5 inventory).
            zone = {"id": zid_cli, "name": args.apex}
            out["steps"].append(
                {
                    "step": "zone_by_id_trust_cli",
                    "zone_id": zid_cli,
                    "note": "GET /zones/{id} denied; proceeding with --zone-id from zone inventory",
                }
            )
    else:
        zone = _zone_lookup(tok, args.apex)

    if not zone or not zone.get("id"):
        out["blocked"] = "zone_not_visible"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("BLOCKED: zone not visible — use --zone-id or Cloudflare dashboard manual rule")
        return 2

    zid = zone["id"]
    out["zone_id"] = zid
    ep = f"/zones/{zid}/rulesets/phases/http_request_dynamic_redirect/entrypoint"
    _, cur = _api(tok, "GET", ep)
    existing = []
    if cur.get("success") and cur.get("result"):
        existing = list((cur.get("result") or {}).get("rules") or [])

    www_rule = _www_studio_rule()
    apex_rule = _apex_studio_rule()
    # drop duplicate studio rules we may have added before
    filtered = [
        r
        for r in existing
        if "oracle v5 (O-P5)" not in (r.get("description") or "")
        and "oracle v6 (O-P5)" not in (r.get("description") or "")
    ]
    merged = [www_rule, apex_rule] + filtered

    body = {"rules": merged}
    out["rule_count_before"] = len(existing)
    out["rule_count_after"] = len(merged)

    if args.dry_run:
        out["action"] = "dry_run"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DRY-RUN ok zone={zid} prepend www+apex /studio -> {args.target_url}")
        return 0

    st, pl = _api(tok, "PUT", ep, body)
    out["steps"].append({"step": "put_entrypoint", "http": st, "success": pl.get("success"), "errors": pl.get("errors")})
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if not pl.get("success"):
        print("PUT failed", pl.get("errors"), file=sys.stderr)
        return 3
    print(f"OK: prepended www+apex /studio rules -> {args.target_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
