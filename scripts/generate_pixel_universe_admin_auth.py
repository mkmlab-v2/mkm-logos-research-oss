#!/usr/bin/env python3
"""
Generate Pixel Universe admin auth header (kid + HMAC).

Header format:
    X-Admin-Auth: <kid>:<unix_ts>:<hex_hmac_sha256>

Message format for signature:
    "<role>:<unix_ts>"
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sys
import time


VALID_ROLES = ("ops_audit_admin", "risk_admin")


def _env_default_kid(role: str) -> str:
    if role == "ops_audit_admin":
        return os.getenv("PIXEL_UNIVERSE_ADMIN_KID_OPS_AUDIT", "ops-v1").strip()
    return os.getenv("PIXEL_UNIVERSE_ADMIN_KID_RISK", "risk-v1").strip()


def _env_default_secret(role: str) -> str:
    if role == "ops_audit_admin":
        return os.getenv("PIXEL_UNIVERSE_ADMIN_SECRET_OPS_AUDIT", "").strip()
    return os.getenv("PIXEL_UNIVERSE_ADMIN_SECRET_RISK", "").strip()


def _build_header(role: str, kid: str, secret: str, ts: int) -> str:
    message = f"{role}:{ts}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{kid}:{ts}:{sig}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate X-Admin-Auth header for Pixel Universe admin endpoints.",
    )
    parser.add_argument("--role", required=True, choices=VALID_ROLES)
    parser.add_argument("--kid", default=None, help="Key ID. Defaults from env by role.")
    parser.add_argument(
        "--secret",
        default=None,
        help="HMAC secret. Defaults from env by role. Never commit real secrets.",
    )
    parser.add_argument(
        "--ts",
        type=int,
        default=None,
        help="Unix timestamp override (default: current time).",
    )
    parser.add_argument(
        "--print-curl",
        action="store_true",
        help="Also print a curl-ready header snippet.",
    )
    args = parser.parse_args()

    role = str(args.role)
    kid = (args.kid or _env_default_kid(role)).strip()
    secret = (args.secret or _env_default_secret(role)).strip()
    ts = int(args.ts if args.ts is not None else int(time.time()))

    if not kid:
        print("error: missing kid (pass --kid or set role-specific env var)", file=sys.stderr)
        return 2
    if not secret:
        print("error: missing secret (pass --secret or set role-specific env var)", file=sys.stderr)
        return 2

    header_value = _build_header(role, kid, secret, ts)
    print(header_value)
    if args.print_curl:
        print(f'curl_header: -H "X-Admin-Auth: {header_value}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
