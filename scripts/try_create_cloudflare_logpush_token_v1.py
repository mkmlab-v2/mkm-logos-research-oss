#!/usr/bin/env python3
"""Auto-create CLOUDFLARE_LOGPUSH_API_TOKEN (Logs Edit + R2 Edit + Turnstile Read) via parent token.

On success: upsert .env + run bundle --assume-bucket-exists --apply

  py scripts/try_create_cloudflare_logpush_token_v1.py
  py scripts/try_create_cloudflare_logpush_token_v1.py --apply-bundle
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
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
OUT = ROOT / "reports" / "cloudflare_logpush_token_create_v1_latest.json"
SECRET = ROOT / "reports" / "cloudflare_logpush_token_secret_LOCAL.json"
ENV_PATH = ROOT / ".env"
KEY = "CLOUDFLARE_LOGPUSH_API_TOKEN"

# Fallback IDs (global permission group catalog; resolved at runtime when parent allows lookup)
FALLBACK_GROUPS: dict[str, str] = {
    "Logs Edit": "9a780f5c5a6a4f8e8c4e4b8e8c4e4b8e",  # placeholder — replaced when lookup works
    "Workers R2 Storage Edit": "2efd5506f9c8494dacb1fa10a3e7d5b6",
    "Turnstile Read": "00000000000000000000000000000000",
}

NEEDED = ("Logs Edit", "Workers R2 Storage Edit", "Turnstile Read")
PARENT_KEYS = (
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
    "CLOUDFLARE_TURNSTILE_API_TOKEN",
    "CLOUDFLARE_RULESETS_API_TOKEN",
    "MKM_MKMLIFE_CF_DEPLOY_TOKEN",
)


def _api(tok: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"success": False, "errors": [{"message": str(e)}]}


def _parent_tokens() -> list[tuple[str, str]]:
    import os

    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for k in PARENT_KEYS:
        v = (
            _read_windows_user_env(k)
            or os.environ.get(k, "").strip()
            or _read_dotenv_key(k)
        ).strip().strip("<>").strip('"').strip("'")
        if not v or v in seen:
            continue
        seen.add(v)
        out.append((k, v))
    return out


def _lookup_groups(tok: str) -> dict[str, str]:
    found: dict[str, str] = {}

    # User token catalog
    for name in NEEDED + ("Logs Write",):
        q = urllib.parse.urlencode({"name": name})
        _, pl = _api(tok, "GET", f"/user/tokens/permission-groups?{q}")
        for g in pl.get("result") or []:
            if not isinstance(g, dict):
                continue
            gn = str(g.get("name") or "").strip()
            if gn == name and gn not in found:
                found[gn] = str(g["id"])

    # Account token catalog (service principal)
    _, acct = _api(tok, "GET", f"/accounts/{ACCOUNT_ID}/tokens/permission-groups")
    for g in acct.get("result") or []:
        if not isinstance(g, dict):
            continue
        gn = str(g.get("name") or "").strip()
        if gn in NEEDED and gn not in found:
            found[gn] = str(g["id"])
        if gn == "Logs Write" and "Logs Edit" not in found:
            found["Logs Edit"] = str(g["id"])

    return found


def _probe_logpush_create(tok: str) -> tuple[int, bool, list[Any]]:
    destination = _read_dotenv_key("TURNSTILE_LOGPUSH_DESTINATION_CONF").strip()
    if not destination:
        return 0, False, [{"message": "no TURNSTILE_LOGPUSH_DESTINATION_CONF"}]
    body = {
        "name": "MKM-turnstile-events-probe-v1",
        "dataset": "turnstile_events",
        "destination_conf": destination,
        "enabled": False,
        "output_options": {"field_names": ["Timestamp", "EventType", "Sitekey"], "timestamp_format": "rfc3339"},
    }
    http, pl = _api(tok, "POST", f"/accounts/{ACCOUNT_ID}/logpush/jobs", body)
    if pl.get("success"):
        job = pl.get("result") if isinstance(pl.get("result"), dict) else {}
        jid = job.get("id")
        if jid:
            _api(tok, "DELETE", f"/accounts/{ACCOUNT_ID}/logpush/jobs/{jid}")
        return http, True, []
    return http, False, pl.get("errors") or []


def _upsert_env(token: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.is_file() else []
    out: list[str] = []
    found = False
    for ln in lines:
        if ln.strip().startswith(f"{KEY}="):
            out.append(f"{KEY}={token}")
            found = True
        else:
            out.append(ln)
    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append("# Turnstile Logpush (Account Logs Edit + Workers R2 Edit + Turnstile Read)")
        out.append(f"{KEY}={token}")
    ENV_PATH.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def _create_user_token(parent: str, groups: dict[str, str]) -> tuple[int, dict[str, Any]]:
    logs_id = groups.get("Logs Edit") or groups.get("Logs Write")
    r2_id = groups.get("Workers R2 Storage Edit")
    ts_id = groups.get("Turnstile Read")
    perm_groups = []
    if logs_id:
        perm_groups.append({"id": logs_id})
    if r2_id:
        perm_groups.append({"id": r2_id})
    if ts_id:
        perm_groups.append({"id": ts_id})
    account_rk = f"com.cloudflare.api.account.{ACCOUNT_ID}"
    policies = [{"effect": "allow", "permission_groups": perm_groups, "resources": {account_rk: "*"}}]
    body = {
        "name": f"MKM-turnstile-logpush-auto-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "policies": policies,
    }
    return _api(parent, "POST", "/user/tokens", body)


def _create_account_token(parent: str, groups: dict[str, str]) -> tuple[int, dict[str, Any]]:
    logs_id = groups.get("Logs Edit") or groups.get("Logs Write")
    r2_id = groups.get("Workers R2 Storage Edit")
    ts_id = groups.get("Turnstile Read")
    perm_groups = []
    if logs_id:
        perm_groups.append({"id": logs_id})
    if r2_id:
        perm_groups.append({"id": r2_id})
    if ts_id:
        perm_groups.append({"id": ts_id})
    body = {
        "name": f"MKM-turnstile-logpush-acct-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "policies": [{"effect": "allow", "permission_groups": perm_groups, "resources": {"*": "*"}}],
    }
    return _api(parent, "POST", f"/accounts/{ACCOUNT_ID}/tokens", body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply-bundle", action="store_true", help="Run logpush bundle after token upsert.")
    args = ap.parse_args()

    doc: dict[str, Any] = {
        "schema": "cloudflare_logpush_token_create_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_id": ACCOUNT_ID,
        "needed_permissions": list(NEEDED),
        "parent_attempts": [],
    }

    # 0) Existing logpush token may already work after user fixed permissions
    import os

    cur = (
        _read_windows_user_env(KEY)
        or os.environ.get(KEY, "").strip()
        or _read_dotenv_key(KEY)
    ).strip()
    if cur:
        http, ok, errs = _probe_logpush_create(cur)
        doc["existing_probe_http"] = http
        doc["existing_probe_ok"] = ok
        doc["existing_probe_errors"] = errs
        if ok:
            doc["decision"] = "EXISTING_TOKEN_OK"
            OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            print(json.dumps(doc, indent=2, ensure_ascii=False))
            if args.apply_bundle:
                return subprocess.call(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "provision_turnstile_logpush_r2_bundle_v1.py"),
                        "--assume-bucket-exists",
                        "--apply",
                    ],
                    cwd=str(ROOT),
                )
            return 0

    created_value = ""
    for parent_key, parent_tok in _parent_tokens():
        attempt: dict[str, Any] = {"parent_key": parent_key, "parent_fp": token_fingerprint(parent_tok)}
        groups = _lookup_groups(parent_tok)
        attempt["permission_groups"] = groups
        missing = [n for n in NEEDED if n not in groups and not (n == "Logs Edit" and "Logs Write" in groups)]
        attempt["missing"] = missing

        if not groups.get("Logs Edit") and not groups.get("Logs Write"):
            attempt["create_skipped"] = "no_logs_group_lookup"
            doc["parent_attempts"].append(attempt)
            continue

        for mode in ("user", "account"):
            if mode == "user":
                st, pl = _create_user_token(parent_tok, groups)
            else:
                st, pl = _create_account_token(parent_tok, groups)
            attempt[f"{mode}_create_http"] = st
            attempt[f"{mode}_create_success"] = bool(pl.get("success"))
            attempt[f"{mode}_create_errors"] = pl.get("errors")
            if pl.get("success"):
                val = str((pl.get("result") or {}).get("value") or "").strip()
                if val:
                    created_value = val
                    attempt["created_via"] = mode
                    doc["parent_attempts"].append(attempt)
                    break
        if created_value:
            break
        doc["parent_attempts"].append(attempt)

    if not created_value:
        doc["decision"] = "BLOCKED_PARENT_CANNOT_CREATE"
        doc["human_gate"] = (
            "Parent tokens lack User/Account API Tokens Write or permission-group lookup. "
            "Run: powershell -File scripts/Open-TurnstileLogpushApiTokenPrefill_v1.ps1 "
            "then py scripts/sync_cloudflare_logpush_token_to_env_v1.py --token cfut_..."
        )
        doc["tier3_prefill"] = "scripts/Open-TurnstileLogpushApiTokenPrefill_v1.ps1"
        OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 1

    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(
        json.dumps(
            {
                "schema": "cloudflare_logpush_token_secret_local_v1",
                "generated_at_utc": doc["generated_at_utc"],
                "token_env_key": KEY,
                "token_value": created_value,
                "token_fingerprint": token_fingerprint(created_value),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _upsert_env(created_value)

    probe_http, probe_ok, probe_errs = _probe_logpush_create(created_value)
    doc["new_token_probe_http"] = probe_http
    doc["new_token_probe_ok"] = probe_ok
    doc["new_token_probe_errors"] = probe_errs
    doc["env_updated"] = str(ENV_PATH)
    doc["decision"] = "CREATED_AND_PROBED" if probe_ok else "CREATED_BUT_PROBE_FAILED"

    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))

    if not probe_ok:
        return 2

    if args.apply_bundle:
        return subprocess.call(
            [
                sys.executable,
                str(ROOT / "scripts" / "provision_turnstile_logpush_r2_bundle_v1.py"),
                "--assume-bucket-exists",
                "--apply",
            ],
            cwd=str(ROOT),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
