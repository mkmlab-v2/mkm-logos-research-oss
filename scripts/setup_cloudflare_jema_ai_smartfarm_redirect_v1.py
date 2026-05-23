#!/usr/bin/env python3
"""jema-ai.com /smartfarm* -> farm.jema-ai.com (308) via Cloudflare dynamic redirect.

Prepends path-specific rule ahead of apex-wide jema-ai.com -> app.jema-ai.com rules.
SSOT nginx fallback: scripts/deploy/linux/apply_jema_ai_com_apex_nginx_v1.sh

Token: MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN or CLOUDFLARE_RULESETS_API_TOKEN when scoped to
**jema-ai.com** + Zone Rulesets Edit (dynamic redirect). jemaai.cloud-only WAF token is NOT enough.

  py scripts/check_cloudflare_token_roles_v1.py   # triage first
  py scripts/setup_cloudflare_jema_ai_smartfarm_redirect_v1.py --dry-run
  py scripts/setup_cloudflare_jema_ai_smartfarm_redirect_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import (  # noqa: E402
    JEMA_AI_ZONE_ID,
    resolve_cloudflare_jema_ai_redirect_token,
    token_fingerprint,
)

DEFAULT_OUT = ROOT / "reports" / "cloudflare_jema_ai_smartfarm_redirect_latest.json"
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


def _verify(tok: str) -> tuple[int, bool]:
    st, pl = _api(tok, "GET", "/user/tokens/verify")
    return st, bool(pl.get("success"))


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


def _recurrence_fix() -> dict:
    return {
        "misdiagnosis_avoid": [
            "token_expired_when_verify_ok",
            "create_new_CLOUDFLARE_API_TOKEN_daily",
            "use_jemaai_cloud_waf_token_without_jema_ai_zone",
        ],
        "one_time_fix_ko": [
            "CF 대시보드 → API Tokens → 기존 CLOUDFLARE_RULESETS_API_TOKEN(cfut_5… 지문) 편집 → "
            "jema-ai.com 존에 Zone Read + Zone Rulesets Edit 추가 (jemaai.cloud만 있으면 부족).",
            "또는 1회: jema-ai.com 전용 MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN → User env + sync_required_env_to_user.ps1",
            "진단 SSOT: py scripts/check_cloudflare_token_roles_v1.py → jema_ai_dynamic_redirect",
            "nginx 2-hop 폴백은 이미 동작 — CF 1-hop은 선택 최적화",
        ],
        "triage": "py scripts/check_cloudflare_token_roles_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zone-id", default=JEMA_AI_ZONE_ID)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-preflight", action="store_true", help="internal only")
    args = ap.parse_args()

    tok, tok_src = resolve_cloudflare_jema_ai_redirect_token()
    if not tok:
        print(
            "Missing token: set MKM_CLOUDFLARE_JEMA_AI_REDIRECT_TOKEN or CLOUDFLARE_RULESETS_API_TOKEN "
            "(jema-ai.com + Zone Rulesets Edit)",
            file=sys.stderr,
        )
        return 1

    zid = args.zone_id.strip()
    ep = f"/zones/{zid}/rulesets/phases/http_request_dynamic_redirect/entrypoint"

    verify_st, verify_ok = _verify(tok)
    get_st, cur = _api(tok, "GET", ep)
    entry_ok = bool(cur.get("success"))
    existing = list((cur.get("result") or {}).get("rules") or []) if entry_ok else []
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
        "token_source": tok_src,
        "token_fingerprint": token_fingerprint(tok),
        "token_verify_http": verify_st,
        "token_verify_ok": verify_ok,
        "entrypoint_get_http": get_st,
        "entrypoint_get_ok": entry_ok,
        "rule_count_before": len(existing),
        "rule_count_after": len(merged),
        "recurrence_fix": _recurrence_fix(),
    }

    if not args.skip_preflight and not args.dry_run and not entry_ok:
        out["action"] = "preflight_blocked"
        out["blocker"] = (
            "jema_ai_dynamic_redirect_scope"
            if verify_ok and get_st in (401, 403)
            else f"entrypoint_get_http_{get_st}"
        )
        out["errors"] = cur.get("errors")
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"BLOCKED: token verify={verify_ok} entrypoint GET {get_st} — "
            "jema-ai.com Zone Rulesets scope missing (NOT expiry). "
            "Run: py scripts/check_cloudflare_token_roles_v1.py",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        out["action"] = "dry_run"
        if not entry_ok:
            out["preflight_warning"] = "entrypoint GET failed — live PUT will block until jema-ai.com Zone Rulesets scope added"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"DRY-RUN ok zone={zid} jema-ai.com /smartfarm -> farm.jema-ai.com (308)")
        return 0 if entry_ok else 2

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
