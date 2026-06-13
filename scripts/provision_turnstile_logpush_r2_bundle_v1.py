#!/usr/bin/env python3
"""Recommended Turnstile Logpush bundle: R2 bucket + scoped token + .env + job apply.

Never prints secrets. Local cache: reports/cloudflare_turnstile_logpush_r2_LOCAL.json

  py scripts/provision_turnstile_logpush_r2_bundle_v1.py --dry-run
  py scripts/provision_turnstile_logpush_r2_bundle_v1.py --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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
BUCKET_NAME = "mkm-turnstile-logs"
BUCKET_PREFIX = f"{BUCKET_NAME}/turnstile/{{DATE}}"
LOCAL = ROOT / "reports" / "cloudflare_turnstile_logpush_r2_LOCAL.json"
ENV_PATH = ROOT / ".env"
OUT = ROOT / "docs" / "final" / "artifacts" / "turnstile_logpush_r2_bundle_v1_latest.json"
TOKEN_KEYS = (
    "CLOUDFLARE_LOGPUSH_API_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
)
R2_TOKEN_NAME = "MKM-turnstile-logpush-r2-v1"
R2_BUCKET_ITEM_WRITE = "2efd5506f9c8494dacb1fa10a3e7d5b6"


def _api(tok: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
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
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {"success": False, "errors": [{"message": str(e)}]}
        return e.code, payload


def _redact_destination(conf: str) -> str:
    if not conf:
        return ""
    if "?" in conf:
        return conf.split("?", 1)[0] + "?[REDACTED_QUERY]"
    return conf


def _bucket_resource(bucket: str) -> str:
    return f"com.cloudflare.edge.r2.bucket.{ACCOUNT_ID}_default_{bucket}"


def _build_destination_conf(access_key_id: str, secret_access_key: str) -> str:
    return (
        f"r2://{BUCKET_PREFIX}"
        f"?account-id={ACCOUNT_ID}"
        f"&access-key-id={access_key_id}"
        f"&secret-access-key={secret_access_key}"
    )


def _resolve_permission_group_id(tok: str, name: str, fallback: str) -> str:
    http, body = _api(tok, "GET", f"/accounts/{ACCOUNT_ID}/tokens/permission_groups")
    if not body.get("success"):
        return fallback
    for group in body.get("result") or []:
        if not isinstance(group, dict):
            continue
        if str(group.get("name") or "") == name:
            return str(group.get("id") or fallback)
    return fallback


def _list_buckets(tok: str) -> tuple[bool, list[str]]:
    http, body = _api(tok, "GET", f"/accounts/{ACCOUNT_ID}/r2/buckets")
    if not body.get("success"):
        return False, []
    buckets = body.get("result", {}).get("buckets") if isinstance(body.get("result"), dict) else None
    names: list[str] = []
    if isinstance(buckets, list):
        for b in buckets:
            if isinstance(b, dict) and b.get("name"):
                names.append(str(b["name"]))
    return True, names


def _ensure_bucket(tok: str, report: dict[str, Any]) -> bool:
    ok, names = _list_buckets(tok)
    report["r2_list_ok"] = ok
    report["r2_buckets"] = names
    if BUCKET_NAME in names:
        report["r2_bucket_action"] = "exists"
        return True
    http, body = _api(tok, "POST", f"/accounts/{ACCOUNT_ID}/r2/buckets", {"name": BUCKET_NAME})
    report["r2_create_http"] = http
    report["r2_create_success"] = bool(body.get("success"))
    report["r2_create_errors"] = body.get("errors")
    if body.get("success"):
        report["r2_bucket_action"] = "created"
        return True
    # Bucket might exist but list failed, or name taken globally
    if http == 409:
        report["r2_bucket_action"] = "exists_conflict"
        return True
    report["r2_bucket_action"] = "failed"
    return False


def _load_r2_keys_from_env() -> dict[str, str] | None:
    import os

    ak = (
        _read_windows_user_env("MKM_R2_LOGPUSH_ACCESS_KEY_ID")
        or os.environ.get("MKM_R2_LOGPUSH_ACCESS_KEY_ID", "").strip()
        or _read_dotenv_key("MKM_R2_LOGPUSH_ACCESS_KEY_ID")
    ).strip()
    sec = (
        _read_windows_user_env("MKM_R2_LOGPUSH_SECRET_ACCESS_KEY")
        or os.environ.get("MKM_R2_LOGPUSH_SECRET_ACCESS_KEY", "").strip()
        or _read_dotenv_key("MKM_R2_LOGPUSH_SECRET_ACCESS_KEY")
    ).strip()
    if not ak or not sec:
        return None
    conf = _build_destination_conf(ak, sec)
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(
        json.dumps(
            {
                "schema": "cloudflare_turnstile_logpush_r2_local_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "bucket": BUCKET_NAME,
                "access_key_id": ak,
                "destination_conf": conf,
                "token_name": "dashboard_r2_api_token",
                "source": "env_r2_keys",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"destination_conf": conf, "access_key_id": ak, "source": "env_r2_keys"}


def _load_cached_destination() -> dict[str, str] | None:
    if not LOCAL.is_file():
        return None
    try:
        doc = json.loads(LOCAL.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    conf = str(doc.get("destination_conf") or "").strip()
    if conf and doc.get("bucket") == BUCKET_NAME:
        return {
            "destination_conf": conf,
            "access_key_id": str(doc.get("access_key_id") or ""),
            "source": "local_cache",
        }
    return None


def _create_r2_scoped_token(tok: str, report: dict[str, Any]) -> dict[str, str] | None:
    write_id = _resolve_permission_group_id(
        tok, "Workers R2 Storage Bucket Item Write", R2_BUCKET_ITEM_WRITE
    )
    body = {
        "name": R2_TOKEN_NAME,
        "policies": [
            {
                "effect": "allow",
                "resources": {_bucket_resource(BUCKET_NAME): "*"},
                "permission_groups": [{"id": write_id}],
            }
        ],
    }
    http, resp = _api(tok, "POST", f"/accounts/{ACCOUNT_ID}/tokens", body)
    report["r2_token_create_http"] = http
    report["r2_token_create_success"] = bool(resp.get("success"))
    report["r2_token_create_errors"] = resp.get("errors")
    result = resp.get("result")
    if not resp.get("success") or not isinstance(result, dict):
        return None
    token_id = str(result.get("id") or "").strip()
    token_value = str(result.get("value") or "").strip()
    if not token_id or not token_value:
        return None
    secret = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
    conf = _build_destination_conf(token_id, secret)
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    LOCAL.write_text(
        json.dumps(
            {
                "schema": "cloudflare_turnstile_logpush_r2_local_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "bucket": BUCKET_NAME,
                "access_key_id": token_id,
                "destination_conf": conf,
                "token_name": R2_TOKEN_NAME,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"destination_conf": conf, "access_key_id": token_id, "source": "api_created"}


def _upsert_env_destination(destination_conf: str) -> None:
    key = "TURNSTILE_LOGPUSH_DESTINATION_CONF"
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.is_file() else []
    present = False
    new_lines: list[str] = []
    for ln in lines:
        if ln.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={destination_conf}")
            present = True
        else:
            new_lines.append(ln)
    if not present:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append("# Turnstile Logpush → R2 (auto bundle)")
        new_lines.append(f"{key}={destination_conf}")
    ENV_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Create resources and apply logpush job.")
    ap.add_argument(
        "--assume-bucket-exists",
        action="store_true",
        help="Skip R2 list/create probe (bucket already created in dashboard).",
    )
    args = ap.parse_args()
    dry_run = not args.apply

    tok, tok_src = resolve_cloudflare_token(extra_keys=TOKEN_KEYS)
    report: dict[str, Any] = {
        "schema": "turnstile_logpush_r2_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": dry_run,
        "research_only": True,
        "account_id": ACCOUNT_ID,
        "bucket": BUCKET_NAME,
        "bucket_prefix": BUCKET_PREFIX,
        "token_source": tok_src or "missing",
        "token_fingerprint": token_fingerprint(tok) if tok else None,
        "reproduce": "py scripts/provision_turnstile_logpush_r2_bundle_v1.py --apply",
    }

    if not tok:
        report["decision"] = "BLOCKED_NO_TOKEN"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    if not args.assume_bucket_exists and not _ensure_bucket(tok, report):
        report["decision"] = "BLOCKED_R2_BUCKET"
        report["human_gate"] = (
            "Grant Account Workers R2 Storage Edit + Logs Edit on CLOUDFLARE_LOGPUSH_API_TOKEN, "
            "or create bucket mkm-turnstile-logs in dashboard then rerun with --assume-bucket-exists"
        )
        report["tier3_scripts"] = [
            "powershell -File scripts/Open-TurnstileLogpushR2Bucket_v1.ps1",
            "powershell -File scripts/Open-TurnstileLogpushApiTokenTemplate_v1.ps1",
        ]
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    if args.assume_bucket_exists:
        report["r2_bucket_action"] = "assumed_exists"
        report["r2_bucket_name"] = BUCKET_NAME

    dest_info = _load_r2_keys_from_env() or _load_cached_destination()
    if not dest_info:
        dest_info = _create_r2_scoped_token(tok, report)
    else:
        report["r2_token_source"] = "local_cache"

    if not dest_info:
        report["decision"] = "BLOCKED_R2_TOKEN"
        report["human_gate"] = (
            "Option A: CLOUDFLARE_LOGPUSH_API_TOKEN (Logs Edit + Workers R2 Storage Edit) in .env, then --apply. "
            "Option B: R2 → Manage API Tokens → Object Read&Write on mkm-turnstile-logs; set "
            "MKM_R2_LOGPUSH_ACCESS_KEY_ID + MKM_R2_LOGPUSH_SECRET_ACCESS_KEY in .env"
        )
        report["tier3_open"] = f"https://dash.cloudflare.com/{ACCOUNT_ID}/r2/api-tokens"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    destination_conf = dest_info["destination_conf"]
    report["destination_conf_redacted"] = _redact_destination(destination_conf)
    report["r2_token_source"] = dest_info.get("source")

    validate_http, validate_body = _api(
        tok,
        "POST",
        f"/accounts/{ACCOUNT_ID}/logpush/validate/destination",
        {"destination_conf": destination_conf},
    )
    report["validate_http"] = validate_http
    report["validate_success"] = bool(validate_body.get("success"))
    report["validate_errors"] = validate_body.get("errors")

    if dry_run:
        report["decision"] = "READY_FOR_APPLY" if report["validate_success"] else "VALIDATE_FAILED"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["validate_success"] else 2

    _upsert_env_destination(destination_conf)
    report["env_updated"] = str(ENV_PATH)

    child = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "provision_turnstile_logpush_job_v1.py"), "--apply"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    report["logpush_child_exit"] = child.returncode
    if child.stdout.strip():
        try:
            report["logpush_child"] = json.loads(child.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            report["logpush_child_stdout_tail"] = child.stdout.strip()[-500:]
    if child.stderr.strip():
        report["logpush_child_stderr_tail"] = child.stderr.strip()[-500:]

    report["decision"] = "APPLIED" if child.returncode == 0 else "APPLY_FAILED"
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return child.returncode


if __name__ == "__main__":
    raise SystemExit(main())
