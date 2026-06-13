#!/usr/bin/env python3
"""Provision Turnstile Events Logpush job (account-scoped, dry-run default).

Dataset: turnstile_events · SSOT artifact:
  docs/final/artifacts/turnstile_logpush_job_provision_v1_latest.json

Requires:
  - API token with Account Logpush Edit (+ destination credentials in destination_conf)
  - TURNSTILE_LOGPUSH_DESTINATION_CONF in .env (e.g. r2://bucket/path?...)

  py scripts/provision_turnstile_logpush_job_v1.py --dry-run
  py scripts/provision_turnstile_logpush_job_v1.py --apply
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
from build_turnstile_logpush_readiness_checklist_v1 import LOGPUSH_FIELDS  # noqa: E402
from mkm_cloudflare_token_v1 import (  # noqa: E402
    _read_dotenv_key,
    _read_windows_user_env,
    resolve_cloudflare_token,
    token_fingerprint,
)

ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"
DATASET = "turnstile_events"
JOB_NAME = "MKM-turnstile-events-v1"
OUT = ROOT / "docs" / "final" / "artifacts" / "turnstile_logpush_job_provision_v1_latest.json"
TOKEN_KEYS = (
    "CLOUDFLARE_LOGPUSH_API_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "CF_API_TOKEN",
)


def _env_key(key: str) -> str:
    import os

    v = _read_windows_user_env(key) or os.environ.get(key, "").strip() or _read_dotenv_key(key)
    return v.strip().strip("<>").strip('"').strip("'")


def _api(tok: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = f"https://api.cloudflare.com/client/v4{path}"
    headers = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    data = None
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


def _redact_destination(conf: str) -> str:
    if not conf:
        return ""
    if "?" in conf:
        base, _ = conf.split("?", 1)
        return f"{base}?[REDACTED_QUERY]"
    return conf


def _find_turnstile_job(jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if str(job.get("dataset") or "") == DATASET:
            return job
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true", help="Create job when absent (disables dry-run).")
    ap.add_argument("--name", default=JOB_NAME)
    args = ap.parse_args()
    dry_run = not args.apply

    destination_conf = _env_key("TURNSTILE_LOGPUSH_DESTINATION_CONF")
    tok, tok_src = resolve_cloudflare_token(extra_keys=TOKEN_KEYS)

    report: dict[str, Any] = {
        "schema": "turnstile_logpush_job_provision_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": dry_run,
        "research_only": True,
        "account_id": ACCOUNT_ID,
        "dataset": DATASET,
        "job_name": args.name,
        "destination_conf_redacted": _redact_destination(destination_conf),
        "token_source": tok_src or "missing",
        "token_fingerprint": token_fingerprint(tok) if tok else None,
        "field_contract": list(LOGPUSH_FIELDS),
        "reproduce": "py scripts/provision_turnstile_logpush_job_v1.py --dry-run",
    }

    if not tok:
        report["decision"] = "BLOCKED_NO_TOKEN"
        report["human_gate"] = "Set CLOUDFLARE_LOGPUSH_API_TOKEN (Logpush Edit) or CLOUDFLARE_API_TOKEN"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    if not destination_conf:
        report["decision"] = "BLOCKED_NO_DESTINATION"
        report["human_gate"] = (
            "Set TURNSTILE_LOGPUSH_DESTINATION_CONF in .env "
            "(e.g. r2://mkm-logs/turnstile?account-id=...&access-key-id=...&secret-access-key=...)"
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    list_http, list_body = _api(tok, "GET", f"/accounts/{ACCOUNT_ID}/logpush/jobs")
    report["list_http"] = list_http
    report["list_success"] = bool(list_body.get("success"))
    jobs = list_body.get("result") if isinstance(list_body.get("result"), list) else []
    existing = _find_turnstile_job(jobs)
    report["existing_job"] = (
        {
            "id": existing.get("id"),
            "enabled": existing.get("enabled"),
            "dataset": existing.get("dataset"),
            "destination_conf_redacted": _redact_destination(str(existing.get("destination_conf") or "")),
        }
        if existing
        else None
    )

    validate_http, validate_body = _api(
        tok,
        "POST",
        f"/accounts/{ACCOUNT_ID}/logpush/validate/destination",
        {"destination_conf": destination_conf},
    )
    report["validate_http"] = validate_http
    report["validate_success"] = bool(validate_body.get("success"))
    report["validate_errors"] = validate_body.get("errors")

    if existing:
        report["decision"] = "ALREADY_PRESENT"
        report["action"] = "none"
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    job_body = {
        "name": args.name,
        "dataset": DATASET,
        "destination_conf": destination_conf,
        "enabled": True,
        "output_options": {
            "field_names": list(LOGPUSH_FIELDS),
            "timestamp_format": "rfc3339",
        },
    }
    report["planned_job"] = {
        **job_body,
        "destination_conf": _redact_destination(destination_conf),
    }

    if dry_run:
        report["decision"] = "READY_FOR_APPLY"
        report["action"] = "dry_run_only"
        report["apply_command"] = "py scripts/provision_turnstile_logpush_job_v1.py --apply"
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["validate_success"] else 2

    create_http, create_body = _api(tok, "POST", f"/accounts/{ACCOUNT_ID}/logpush/jobs", job_body)
    report["create_http"] = create_http
    report["create_success"] = bool(create_body.get("success"))
    report["create_errors"] = create_body.get("errors")
    created = create_body.get("result")
    if isinstance(created, dict):
        report["created_job_id"] = created.get("id")
    report["decision"] = "CREATED" if report["create_success"] else "CREATE_FAILED"
    report["action"] = "create"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["create_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
