#!/usr/bin/env python3
"""Provision or update jema-ai Turnstile widget via Cloudflare API (Tier 1).

Never prints secret values. Secret → reports/cloudflare_turnstile_jema_ai_secret_LOCAL.json (local only).

  py scripts/provision_turnstile_jema_ai_widget_v1.py --dry-run
  py scripts/provision_turnstile_jema_ai_widget_v1.py
  py scripts/provision_turnstile_jema_ai_widget_v1.py --update-sitekey 0x...
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import (  # noqa: E402
    _read_dotenv_key,
    _read_windows_user_env,
    resolve_cloudflare_token,
    token_fingerprint,
)

ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"
OUT = ROOT / "docs" / "final" / "artifacts" / "turnstile_jema_ai_widget_provision_v1_latest.json"
SECRET_PATH = ROOT / "reports" / "cloudflare_turnstile_jema_ai_secret_LOCAL.json"
DEFAULT_NAME = "MKM-jema-ai-app-v1"
DEFAULT_DOMAINS = ("jema-ai.com", "app.jema-ai.com", "www.jema-ai.com")
TOKEN_KEYS = (
    "CLOUDFLARE_TURNSTILE_API_TOKEN",
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
)


def _token_for_key(key: str) -> tuple[str, str]:
    import os

    def _norm(v: str) -> str:
        return v.strip().strip("<>").strip('"').strip("'")

    v = _read_windows_user_env(key)
    if v:
        return _norm(v), f"user_env:{key}"
    v = os.environ.get(key, "").strip()
    if v:
        return _norm(v), f"process_env:{key}"
    v = _read_dotenv_key(key)
    if v:
        return _norm(v), f".env:{key}"
    return "", "missing"


def _resolve_turnstile_token() -> tuple[str, str]:
    for key in TOKEN_KEYS:
        tok, src = _token_for_key(key)
        if tok:
            return tok, src
    return "", "missing"


def _api(
    tok: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    data = None
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {"success": False, "errors": [{"message": str(e)}]}
        return e.code, payload


def _list_widgets(tok: str) -> dict[str, Any]:
    code, body = _api(tok, "GET", f"/accounts/{ACCOUNT_ID}/challenges/widgets")
    return {"http": code, "success": bool(body.get("success")), "body": body}


def _redact_result(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return result
    out = dict(result)
    if "secret" in out:
        out["secret"] = "[REDACTED_SAVED_LOCAL]"
    return out


def _save_secret(sitekey: str, secret: str, name: str, domains: list[str]) -> None:
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": "cloudflare_turnstile_jema_ai_secret_v1",
        "note": "Git commit 금지. .env 또는 DPAPI 경로로만 승격.",
        "account_id": ACCOUNT_ID,
        "widget_name": name,
        "domains": domains,
        "TURNSTILE_SITEKEY": sitekey,
        "TURNSTILE_SECRET_KEY": secret,
        "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    SECRET_PATH.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def _prune_legacy_widgets(
    tok: str,
    *,
    legacy_names: set[str],
    keep_name: str,
) -> list[dict[str, Any]]:
    pruned: list[dict[str, Any]] = []
    probe = _list_widgets(tok)
    if not probe["success"]:
        return pruned
    for w in probe["body"].get("result") or []:
        if not isinstance(w, dict):
            continue
        name = str(w.get("name") or "")
        sitekey = str(w.get("sitekey") or "")
        if not sitekey:
            continue
        if name == keep_name:
            continue
        if name.lower() not in legacy_names:
            continue
        http, resp = _api(tok, "DELETE", f"/accounts/{ACCOUNT_ID}/challenges/widgets/{sitekey}")
        pruned.append(
            {
                "name": name,
                "sitekey": sitekey,
                "http": http,
                "success": bool(resp.get("success")),
                "errors": resp.get("errors"),
            }
        )
    return pruned


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--name", default=DEFAULT_NAME)
    ap.add_argument(
        "--domains",
        default=",".join(DEFAULT_DOMAINS),
        help="Comma-separated hostnames",
    )
    ap.add_argument("--update-sitekey", default="", help="PUT existing widget by sitekey")
    ap.add_argument("--mode", default="managed", choices=("managed", "invisible", "non-interactive"))
    ap.add_argument(
        "--prune-legacy-names",
        default="mkmlab",
        help="Comma-separated legacy widget names to delete (default: mkmlab). Use empty to skip.",
    )
    args = ap.parse_args()

    domains = [d.strip() for d in args.domains.split(",") if d.strip()]
    legacy_names = {
        n.strip().lower()
        for n in (args.prune_legacy_names or "").split(",")
        if n.strip()
    }
    tok, tok_src = _resolve_turnstile_token()
    body = {"name": args.name, "domains": domains, "mode": args.mode, "bot_fight_mode": False}

    report: dict[str, Any] = {
        "schema": "turnstile_jema_ai_widget_provision_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": bool(args.dry_run),
        "account_id": ACCOUNT_ID,
        "requested": body,
        "token_source": tok_src,
        "token_fingerprint": token_fingerprint(tok) if tok else None,
        "secret_path": str(SECRET_PATH),
        "reproduce": "py scripts/provision_turnstile_jema_ai_widget_v1.py",
    }

    if not tok:
        report["decision"] = "BLOCKED_NO_TOKEN"
        report["human_gate"] = "Create API token with Account Turnstile Edit → reports/cloudflare_turnstile_jema_ai_secret_LOCAL.json or .env CLOUDFLARE_TURNSTILE_API_TOKEN"
        report["open_scripts"] = [
            "powershell -File scripts/Open-TurnstileApiTokenTemplate_v1.ps1",
            "powershell -File scripts/Open-TurnstileWidgetAdd_v1.ps1",
        ]
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    if args.dry_run:
        list_probe = _list_widgets(tok)
        report["list_probe_http"] = list_probe["http"]
        report["list_probe_success"] = list_probe["success"]
        report["decision"] = "DRY_RUN"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if legacy_names:
        report["pruned_legacy"] = _prune_legacy_widgets(
            tok, legacy_names=legacy_names, keep_name=args.name
        )

    if args.update_sitekey:
        path = f"/accounts/{ACCOUNT_ID}/challenges/widgets/{args.update_sitekey}"
        http, resp = _api(tok, "PUT", path, body)
        action = "update"
    else:
        list_probe = _list_widgets(tok)
        existing = []
        if list_probe["success"]:
            for w in list_probe["body"].get("result") or []:
                if isinstance(w, dict):
                    existing.append(w)
        match = next(
            (
                w
                for w in existing
                if w.get("name") == args.name
                or set(domains).issubset(set(w.get("domains") or []))
            ),
            None,
        )
        if match and match.get("sitekey"):
            path = f"/accounts/{ACCOUNT_ID}/challenges/widgets/{match['sitekey']}"
            http, resp = _api(tok, "PUT", path, body)
            action = "update_matched"
            report["matched_sitekey"] = match.get("sitekey")
        else:
            path = f"/accounts/{ACCOUNT_ID}/challenges/widgets"
            http, resp = _api(tok, "POST", path, body)
            action = "create"

    report["action"] = action
    report["http"] = http
    report["api_success"] = bool(resp.get("success"))
    report["result_redacted"] = _redact_result(resp.get("result") if isinstance(resp.get("result"), dict) else None)
    if resp.get("errors"):
        report["errors"] = resp.get("errors")

    if resp.get("success") and isinstance(resp.get("result"), dict):
        result = resp["result"]
        sitekey = str(result.get("sitekey") or "")
        secret = str(result.get("secret") or "")
        if sitekey and secret:
            _save_secret(sitekey, secret, args.name, domains)
            report["decision"] = "PROVISIONED"
            report["sitekey"] = sitekey
        elif sitekey:
            report["decision"] = "UPDATED_NO_NEW_SECRET"
            report["sitekey"] = sitekey
        else:
            report["decision"] = "API_OK_MISSING_KEYS"
    elif http == 403:
        report["decision"] = "BLOCKED_TURNSTILE_SCOPE"
        report["human_gate"] = "Token lacks Account:Turnstile:Edit — run Open-TurnstileApiTokenTemplate_v1.ps1 then retry"
        report["open_scripts"] = [
            "powershell -File scripts/Open-TurnstileApiTokenTemplate_v1.ps1",
            "powershell -File scripts/Open-TurnstileWidgetAdd_v1.ps1",
        ]
    else:
        report["decision"] = "API_FAILED"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n[turnstile_provision] decision={report['decision']}", file=sys.stderr)
    return 0 if report.get("decision") in ("PROVISIONED", "UPDATED_NO_NEW_SECRET") else 1


if __name__ == "__main__":
    raise SystemExit(main())
