#!/usr/bin/env python3
"""Print curl-ready headers for GET /api/public-events/latest HMAC auth.

Uses the same canonical string as public_event_gateway.verify_public_event_get_hmac.
Secret: env PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET or --secret (do not commit secrets).
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_GATEWAY = (
    _ROOT
    / "projects"
    / "bitcoin-trading"
    / "ops"
    / "windows-rehearsal"
    / "jemaai-cloud-mvp"
    / "public_event_gateway.py"
)


def _load_build():
    spec = importlib.util.spec_from_file_location("peg_sign", _GATEWAY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.build_public_event_get_hmac_signature


def main() -> int:
    ap = argparse.ArgumentParser(description="Sign GET /api/public-events/latest for HMAC gateway auth")
    ap.add_argument("--secret", default="", help="Shared secret (otherwise env PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET)")
    ap.add_argument("--path", default="/api/public-events/latest")
    ap.add_argument("--timestamp", default="", help="Unix seconds (default: now)")
    args = ap.parse_args()
    secret = (args.secret or os.environ.get("PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET") or "").strip()
    if not secret:
        print("missing secret: pass --secret or set PUBLIC_EVENT_GATEWAY_GET_HMAC_SECRET", file=sys.stderr)
        return 2
    ts = str(args.timestamp).strip() or str(int(time.time()))
    build = _load_build()
    sig = build(secret, ts, "GET", args.path)
    print(f"x-mkm-timestamp: {ts}")
    print(f"x-mkm-signature: {sig}")
    base = os.environ.get("PUBLIC_EVENT_GATEWAY_URL", "http://127.0.0.1:8788")
    print(
        f'curl -sS -H "x-mkm-timestamp: {ts}" -H "x-mkm-signature: {sig}" "{base.rstrip("/")}{args.path}"',
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
