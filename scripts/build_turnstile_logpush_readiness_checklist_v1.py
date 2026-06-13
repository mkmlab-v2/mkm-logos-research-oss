#!/usr/bin/env python3
"""Turnstile Logpush readiness checklist (dry-run only — no job creation).

SSOT: docs/final/artifacts/turnstile_logpush_readiness_checklist_v1_latest.json

  py scripts/build_turnstile_logpush_readiness_checklist_v1.py
  py scripts/build_turnstile_logpush_readiness_checklist_v1.py --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "turnstile_logpush_readiness_checklist_v1_latest.json"
ACCOUNT_ID = "646e42cf881ab43043c32430e99d9af4"

LOGPUSH_FIELDS = (
    "ASN",
    "Action",
    "BrowserMajor",
    "BrowserName",
    "ClientIP",
    "CountryCode",
    "EventType",
    "Hostname",
    "OSMajor",
    "OSName",
    "Sitekey",
    "Timestamp",
    "UserAgent",
)


def _key_presence() -> dict[str, bool]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_cloudflare_token_v1 import (  # noqa: E402
        _read_dotenv_key,
        _read_windows_user_env,
    )

    import os

    keys = (
        "CLOUDFLARE_API_TOKEN",
        "CF_API_TOKEN",
        "CLOUDFLARE_RULESETS_API_TOKEN",
        "MKM_MKMLIFE_CF_ANALYTICS_TOKEN",
    )
    out: dict[str, bool] = {}
    for k in keys:
        tok = (
            _read_windows_user_env(k)
            or os.environ.get(k, "").strip()
            or _read_dotenv_key(k)
        )
        out[k] = bool(tok)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if prerequisite checks not PASS (dry-run gates only).",
    )
    args = ap.parse_args()

    presence = _key_presence()
    has_any_cf_token = any(presence.values())

    sys.path.insert(0, str(ROOT / "scripts"))
    from mkm_cloudflare_token_v1 import _read_dotenv_key  # noqa: E402

    import os

    dest = (
        os.environ.get("TURNSTILE_LOGPUSH_DESTINATION_CONF", "").strip()
        or _read_dotenv_key("TURNSTILE_LOGPUSH_DESTINATION_CONF")
    )
    has_destination = bool(dest)

    checks: list[dict[str, Any]] = [
        {
            "id": "L1_changelog_ack",
            "description": "Turnstile Events Logpush dataset documented (2026-06-01).",
            "status": "PASS",
            "evidence_url": "https://developers.cloudflare.com/changelog/post/2026-06-01-log-fields-updated/",
        },
        {
            "id": "L2_field_contract",
            "description": "Expected Logpush fields captured for downstream schema.",
            "status": "PASS",
            "fields": list(LOGPUSH_FIELDS),
        },
        {
            "id": "L3_cf_token_present",
            "description": "At least one Cloudflare API token key present (Logpush setup is Tier 1 API).",
            "status": "PASS" if has_any_cf_token else "BLOCK",
            "key_presence": presence,
        },
        {
            "id": "L4_logpush_scope_human",
            "description": "Account Logpush Edit scope on dedicated token (human CF dashboard — Tier 3 for UI).",
            "status": "TODO",
            "human_action_ko": "API Tokens → Account Log Read + Logpush Edit 확인",
        },
        {
            "id": "L5_destination",
            "description": "Logpush destination (S3/R2/syslog) in TURNSTILE_LOGPUSH_DESTINATION_CONF.",
            "status": "PASS" if has_destination else "TODO",
            "destination_redacted": (
                dest.split("?", 1)[0] + "?[REDACTED]" if "?" in dest else (dest[:40] + "..." if dest else "")
            ),
        },
        {
            "id": "L6_mkm_track_a_isolation",
            "description": "Logpush observability only — no Track A/live trading auto-merge.",
            "status": "PASS",
        },
        {
            "id": "L7_provision_script_dry_run",
            "description": "Job creation via provision script (dry-run default; --apply for POST).",
            "status": "PASS",
            "reproduce": "py scripts/provision_turnstile_logpush_job_v1.py --dry-run",
        },
    ]

    blockers = [c["id"] for c in checks if c["status"] == "BLOCK"]
    todos = [c["id"] for c in checks if c["status"] == "TODO"]
    all_pass = not blockers and not todos

    doc = {
        "schema": "turnstile_logpush_readiness_checklist_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": True,
        "research_only": True,
        "account_id": ACCOUNT_ID,
        "dataset": "Turnstile Events",
        "checks": checks,
        "decision": "READY_FOR_HUMAN_LOGPUSH_SETUP" if not blockers else "BLOCKED_MISSING_TOKEN",
        "blockers": blockers,
        "human_todos": todos,
        "next_commands": [
            "py scripts/check_turnstile_commander_ops_v1.py",
            "py scripts/check_cloudflare_token_roles_v1.py",
            "py scripts/provision_turnstile_logpush_job_v1.py --dry-run",
        ],
        "reproduce": "py scripts/build_turnstile_logpush_readiness_checklist_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    print(f"\n[logpush_checklist] decision={doc['decision']} dry_run=true", file=sys.stderr)

    if args.strict and (blockers or todos):
        return 1
    if blockers:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
