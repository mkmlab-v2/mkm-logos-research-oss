#!/usr/bin/env python3
"""Probe (and optional dry-run plan) CF edge for jemaai.cloud: SSL mode, cache, rate-limit rulesets."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZONE_NAME = "jemaai.cloud"
ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
OUT = ROOT / "reports" / "jemaai_cloud_cf_edge_hardening_v1_latest.json"


def _load_token() -> str:
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CLOUDFLARE_API_TOKEN=") or line.startswith("CF_API_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return (os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN") or "").strip()


def _api(tok: str, method: str, path: str, body: dict | None = None) -> dict:
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"success": False, "errors": [{"message": str(e), "code": e.code}]}


def main() -> int:
    dry = "--dry-run" in sys.argv
    tok = _load_token()
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    out: dict = {
        "schema": "jemaai_cloud_cf_edge_hardening_v1",
        "zone": ZONE_NAME,
        "zone_id": ZONE_ID,
        "dry_run": dry,
        "recommendations": [
            "Origin JSON already uses Cache-Control no-store on slice paths (nginx snippet).",
            "CF: enable rate limit on /public_showroom* and /showroom_* JSON if token has Zone WAF Edit.",
            "CF: cache HTML short TTL only if stale-while-revalidate acceptable; keep API paths bypass.",
        ],
        "not_media_scale": True,
    }

    verify = _api(tok, "GET", "/user/tokens/verify")
    out["token_verify"] = bool(verify.get("success"))
    if not verify.get("success"):
        out["errors"] = verify.get("errors")
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return 2

    ssl = _api(tok, "GET", f"/zones/{ZONE_ID}/settings/ssl")
    out["ssl_mode"] = (ssl.get("result") or {}).get("value")

    sec = _api(tok, "GET", f"/zones/{ZONE_ID}/settings/security_level")
    out["security_level"] = (sec.get("result") or {}).get("value")

    # Rate limit rulesets (phase http_ratelimit) — read-only probe
    rl = _api(tok, "GET", f"/zones/{ZONE_ID}/rulesets/phases/http_ratelimit/entrypoint")
    out["ratelimit_entrypoint"] = {
        "success": rl.get("success"),
        "has_rules": bool((rl.get("result") or {}).get("rules")),
        "rule_count": len((rl.get("result") or {}).get("rules") or []),
        "errors": rl.get("errors"),
    }

    # Cache rules entrypoint probe
    cr = _api(tok, "GET", f"/zones/{ZONE_ID}/rulesets/phases/http_request_cache_settings/entrypoint")
    out["cache_settings_entrypoint"] = {
        "success": cr.get("success"),
        "has_rules": bool((cr.get("result") or {}).get("rules")),
        "rule_count": len((cr.get("result") or {}).get("rules") or []),
        "errors": cr.get("errors"),
    }

    apex = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name={ZONE_NAME}")
    api_host = _api(tok, "GET", f"/zones/{ZONE_ID}/dns_records?name=api.{ZONE_NAME}")
    out["dns"] = {
        "apex": [
            {"type": r.get("type"), "content": r.get("content"), "proxied": r.get("proxied")}
            for r in (apex.get("result") or [])
        ],
        "api": [
            {"type": r.get("type"), "content": r.get("content"), "proxied": r.get("proxied")}
            for r in (api_host.get("result") or [])
        ],
    }

    rl_ok = bool(out["ratelimit_entrypoint"].get("success") and out["ratelimit_entrypoint"].get("has_rules"))
    cache_ok = bool(out["cache_settings_entrypoint"].get("success") and out["cache_settings_entrypoint"].get("has_rules"))
    out["edge_rules_configured"] = rl_ok and cache_ok
    ssl_ok = out["ssl_mode"] in ("full", "strict") if out["ssl_mode"] else None
    out["ssl_ok"] = ssl_ok
    out["ok"] = bool(out["token_verify"] and out["edge_rules_configured"])
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
