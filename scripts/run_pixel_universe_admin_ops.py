#!/usr/bin/env python3
"""
Run Pixel Universe admin operations with signed X-Admin-Auth.

Supported actions:
- unsuspend: POST /api/v1/pixel-universe/admin/agents/{agent_id}/unsuspend
- rotate-audit: POST /api/v1/pixel-universe/admin/audit/rotate
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


VALID_ACTIONS = ("unsuspend", "rotate-audit")
ROLE_BY_ACTION = {
    "unsuspend": "risk_admin",
    "rotate-audit": "ops_audit_admin",
}


@dataclass
class Config:
    base_url: str
    action: str
    agent_id: str | None
    kid: str
    secret: str
    timeout_sec: float
    dry_run: bool


def _env_default_kid(role: str) -> str:
    if role == "ops_audit_admin":
        return os.getenv("PIXEL_UNIVERSE_ADMIN_KID_OPS_AUDIT", "ops-v1").strip()
    return os.getenv("PIXEL_UNIVERSE_ADMIN_KID_RISK", "risk-v1").strip()


def _env_default_secret(role: str) -> str:
    if role == "ops_audit_admin":
        return os.getenv("PIXEL_UNIVERSE_ADMIN_SECRET_OPS_AUDIT", "").strip()
    return os.getenv("PIXEL_UNIVERSE_ADMIN_SECRET_RISK", "").strip()


def _build_admin_auth(role: str, kid: str, secret: str, ts: int) -> str:
    message = f"{role}:{ts}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{kid}:{ts}:{sig}"


def _request_json(url: str, headers: dict[str, str], timeout_sec: float) -> tuple[int, dict]:
    req = urllib.request.Request(url, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8")
        payload = json.loads(raw) if raw else {}
        return resp.status, payload


def run(cfg: Config) -> int:
    role = ROLE_BY_ACTION[cfg.action]
    ts = int(time.time())
    admin_auth = _build_admin_auth(role, cfg.kid, cfg.secret, ts)
    if cfg.action == "unsuspend":
        assert cfg.agent_id is not None
        url = f"{cfg.base_url}/api/v1/pixel-universe/admin/agents/{cfg.agent_id}/unsuspend"
    else:
        url = f"{cfg.base_url}/api/v1/pixel-universe/admin/audit/rotate"

    headers = {"X-Admin-Auth": admin_auth}
    print(f"action={cfg.action}")
    print(f"role={role}")
    print(f"url={url}")
    print(f"header=X-Admin-Auth:{admin_auth}")
    if cfg.dry_run:
        print("dry_run=1 (request not sent)")
        return 0

    try:
        status, body = _request_json(url, headers, cfg.timeout_sec)
        print(f"status={status}")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0 if status == 200 else 1
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print(f"status={e.code}")
        if detail:
            print(detail)
        return 1
    except urllib.error.URLError as e:
        print(f"connection_error={e.reason}")
        print("tip: start api server first in api-services with uvicorn main:app")
        return 1


def parse_args() -> Config:
    parser = argparse.ArgumentParser(description="Run Pixel Universe admin operations.")
    parser.add_argument("--action", required=True, choices=VALID_ACTIONS)
    parser.add_argument("--agent-id", default=None, help="Required when --action unsuspend")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--kid", default=None, help="Overrides role default kid from env")
    parser.add_argument("--secret", default=None, help="Overrides role default secret from env")
    parser.add_argument("--timeout-sec", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    role = ROLE_BY_ACTION[str(args.action)]
    kid = (args.kid or _env_default_kid(role)).strip()
    secret = (args.secret or _env_default_secret(role)).strip()

    if args.action == "unsuspend" and not args.agent_id:
        print("error: --agent-id is required for --action unsuspend", file=sys.stderr)
        raise SystemExit(2)
    if not kid:
        print("error: missing kid (pass --kid or set env var)", file=sys.stderr)
        raise SystemExit(2)
    if not secret:
        print("error: missing secret (pass --secret or set env var)", file=sys.stderr)
        raise SystemExit(2)

    return Config(
        base_url=str(args.base_url).rstrip("/"),
        action=str(args.action),
        agent_id=args.agent_id,
        kid=kid,
        secret=secret,
        timeout_sec=max(1.0, float(args.timeout_sec)),
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
