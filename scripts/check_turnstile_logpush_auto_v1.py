#!/usr/bin/env python3
"""API-only Turnstile Logpush auto-check (no dashboard login).

  py scripts/check_turnstile_logpush_auto_v1.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mkm_cloudflare_token_v1 import _read_dotenv_key, _read_windows_user_env, token_fingerprint  # noqa: E402

ACCOUNT = "646e42cf881ab43043c32430e99d9af4"
OUT = ROOT / "reports" / "turnstile_logpush_auto_check_latest.json"


def _tok() -> str:
    import os

    return (
        _read_windows_user_env("CLOUDFLARE_LOGPUSH_API_TOKEN")
        or os.environ.get("CLOUDFLARE_LOGPUSH_API_TOKEN", "").strip()
        or _read_dotenv_key("CLOUDFLARE_LOGPUSH_API_TOKEN")
    ).strip()


def _api(tok: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def main() -> int:
    tok = _tok()
    dest = _read_dotenv_key("TURNSTILE_LOGPUSH_DESTINATION_CONF").strip()
    doc: dict = {
        "schema": "turnstile_logpush_auto_check_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token_fingerprint": token_fingerprint(tok) if tok else None,
        "reproduce": "py scripts/check_turnstile_logpush_auto_v1.py",
    }
    if not tok:
        doc["decision"] = "BLOCKED_NO_TOKEN"
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 1

    _, acct = _api(tok, "GET", f"/accounts/{ACCOUNT}")
    res = acct.get("result") if isinstance(acct.get("result"), dict) else {}
    doc["account_type"] = res.get("type")
    doc["account_name"] = res.get("name")

    _, jobs_pl = _api(tok, "GET", f"/accounts/{ACCOUNT}/logpush/jobs")
    jobs = jobs_pl.get("result") if isinstance(jobs_pl.get("result"), list) else []
    doc["logpush_job_count"] = len(jobs)
    doc["logpush_datasets"] = [j.get("dataset") for j in jobs if isinstance(j, dict)]

    turnstile = next((j for j in jobs if isinstance(j, dict) and j.get("dataset") == "turnstile_events"), None)
    if turnstile:
        doc["decision"] = "ALREADY_PRESENT"
        doc["turnstile_job_id"] = turnstile.get("id")
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 0

    if dest:
        body = {
            "name": "probe-turnstile-events",
            "dataset": "turnstile_events",
            "destination_conf": dest,
            "enabled": False,
            "output_options": {"field_names": ["Timestamp"], "timestamp_format": "rfc3339"},
        }
        http, pl = _api(tok, "POST", f"/accounts/{ACCOUNT}/logpush/jobs", body)
        doc["create_probe_http"] = http
        if pl.get("success"):
            jid = (pl.get("result") or {}).get("id")
            doc["create_probe"] = "ok"
            if jid:
                _api(tok, "DELETE", f"/accounts/{ACCOUNT}/logpush/jobs/{jid}")
            doc["decision"] = "CAN_CREATE_VIA_API"
        else:
            err = (pl.get("errors") or [{}])[0]
            doc["create_probe_error"] = err
            msg = str(err.get("message") or "")
            if "exceeded max jobs" in msg:
                doc["decision"] = "PLAN_OR_QUOTA_BLOCKED"
                if doc.get("account_type") == "standard":
                    doc["free_path"] = "use_app_turnstile_verify_logs_and_dashboard_analytics"
                    doc["free_ops_check"] = "py scripts/check_turnstile_free_ops_v1.py"
            elif "missing required permissions" in msg:
                if doc.get("account_type") == "standard":
                    doc["decision"] = "FREE_PATH_PLAN_BLOCKED"
                    doc["free_path"] = "use_app_turnstile_verify_logs_and_dashboard_analytics"
                    doc["free_ops_check"] = "py scripts/check_turnstile_free_ops_v1.py"
                else:
                    doc["decision"] = "MISSING_TURNSTILE_OR_LOGS_PERM"
            else:
                doc["decision"] = "CREATE_BLOCKED"
    else:
        doc["decision"] = "NO_DESTINATION_CONF"

    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    ok_decisions = {
        "ALREADY_PRESENT",
        "CAN_CREATE_VIA_API",
        "FREE_PATH_PLAN_BLOCKED",
        "PLAN_OR_QUOTA_BLOCKED",
    }
    if doc.get("account_type") == "standard" and doc["decision"] in {
        "FREE_PATH_PLAN_BLOCKED",
        "PLAN_OR_QUOTA_BLOCKED",
    }:
        return 0
    return 0 if doc["decision"] in ok_decisions else 2


if __name__ == "__main__":
    raise SystemExit(main())
