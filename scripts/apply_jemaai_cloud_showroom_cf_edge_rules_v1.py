#!/usr/bin/env python3
"""Apply jemaai.cloud showroom edge rules via Cloudflare Rulesets API (requires Zone Rulesets Edit).

  py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py --dry-run
  py scripts/apply_jemaai_cloud_showroom_cf_edge_rules_v1.py
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
ZONE_ID = "cf557dfa09436d998416ad849e73c0ec"
OUT = ROOT / "reports" / "jemaai_cloud_showroom_cf_edge_apply_v1_latest.json"

SHOWROOM_HOSTS = '(http.host in {"jemaai.cloud" "www.jemaai.cloud" "api.jemaai.cloud"})'
SHOWROOM_PATH = '(http.request.uri.path contains "/public_showroom" or http.request.uri.path contains "/showroom_")'
RL_DESC = "MKM jemaai showroom path rate limit (v1)"
CACHE_HTML_DESC = "MKM jemaai showroom html bypass (v1)"
CACHE_JSON_DESC = "MKM jemaai showroom json bypass (v1)"


def _load_token() -> str:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_cloudflare_token_v1 import resolve_cloudflare_token  # noqa: E402

    tok, _src = resolve_cloudflare_token(
        extra_keys=("CLOUDFLARE_RULESETS_API_TOKEN", "MKM_CLOUDFLARE_RULESETS_TOKEN")
    )
    return tok


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def _rate_limit_rule() -> dict:
    return {
        "action": "block",
        "expression": f"{SHOWROOM_HOSTS} and {SHOWROOM_PATH}",
        "description": RL_DESC,
        "enabled": True,
        "ratelimit": {
            "characteristics": ["cf.colo.id", "ip.src"],
            # Free/pro plans: CF allows period/mitigation 10 only (not 60).
            "period": 10,
            "requests_per_period": 100,
            "mitigation_timeout": 10,
        },
    }


def _cache_bypass_rule(desc: str, expression: str) -> dict:
    return {
        "action": "set_cache_settings",
        "expression": expression,
        "description": desc,
        "enabled": True,
        "action_parameters": {"cache": False},
    }


def _merge_rules(existing: list, ours: list, descriptions: set[str], *, append_ours: bool = False) -> list:
    kept = [r for r in existing if (r.get("description") or "") not in descriptions]
    return kept + ours if append_ours else ours + kept


def _entrypoint_missing(cur: dict, code: int) -> bool:
    if code == 404:
        return True
    for err in cur.get("errors") or []:
        if err.get("code") == 10003:
            return True
    return False


def _apply_phase(tok: str, phase: str, new_rules: list, descriptions: set[str], dry: bool) -> dict:
    ep = f"/zones/{ZONE_ID}/rulesets/phases/{phase}/entrypoint"
    code, cur = _api(tok, "GET", ep)
    row: dict = {"phase": phase, "http_get": code}
    if cur.get("success"):
        existing = list((cur.get("result") or {}).get("rules") or [])
        row["api_success"] = True
    elif _entrypoint_missing(cur, code):
        existing = []
        row["api_success"] = True
        row["entrypoint_created_on_put"] = True
    else:
        row["api_success"] = False
        row["errors"] = cur.get("errors")
        return row
    merged = _merge_rules(
        existing, new_rules, descriptions, append_ours=(phase == "http_ratelimit")
    )
    row["rule_count_before"] = len(existing)
    row["rule_count_after"] = len(merged)
    if dry:
        row["action"] = "dry_run"
        return row
    body = {"rules": merged}
    code2, put = _api(tok, "PUT", ep, body)
    row["http_put"] = code2
    row["put_success"] = bool(put.get("success"))
    if not put.get("success"):
        row["put_errors"] = put.get("errors")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    tok = _load_token()
    if not tok:
        print("CLOUDFLARE_API_TOKEN missing", file=sys.stderr)
        return 1

    cache_html_expr = (
        '(http.host in {"jemaai.cloud" "www.jemaai.cloud"}) and '
        'http.request.uri.path.extension eq "html" and '
        'http.request.uri.path contains "public_showroom"'
    )
    cache_json_expr = (
        f"{SHOWROOM_HOSTS} and "
        '(http.request.uri.path contains "showroom_" or http.request.uri.path contains "_slice_") and '
        'http.request.uri.path.extension eq "json"'
    )
    cache_rules = [
        _cache_bypass_rule(CACHE_HTML_DESC, cache_html_expr),
        _cache_bypass_rule(CACHE_JSON_DESC, cache_json_expr),
    ]
    cache_desc = {CACHE_HTML_DESC, CACHE_JSON_DESC, "MKM probe create"}

    out: dict = {
        "schema": "jemaai_cloud_showroom_cf_edge_apply_v1",
        "zone_id": ZONE_ID,
        "dry_run": args.dry_run,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dashboard_fallback": "docs/final/JEMAAI_CLOUD_SHOWROOM_CF_EDGE_DASHBOARD_V1.md",
    }

    out["rate_limit"] = _apply_phase(
        tok, "http_ratelimit", [_rate_limit_rule()], {RL_DESC}, args.dry_run
    )
    out["cache_settings"] = _apply_phase(
        tok, "http_request_cache_settings", cache_rules, cache_desc, args.dry_run
    )

    rl_ok = out["rate_limit"].get("api_success") and (
        args.dry_run or out["rate_limit"].get("put_success")
    )
    cache_ok = out["cache_settings"].get("api_success") and (
        args.dry_run or out["cache_settings"].get("put_success")
    )
    out["ok"] = bool(rl_ok and cache_ok)
    out["manual_dashboard_required"] = not out["ok"]

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if not out["ok"]:
        print(
            "BLOCK: apply failed — check token (Zone WAF + Cache Rules) or dashboard:\n"
            "https://dash.cloudflare.com/646e42cf881ab43043c32430e99d9af4/jemaai.cloud",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
