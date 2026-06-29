#!/usr/bin/env python3
"""Upsert CLOUDFLARE_LOGPUSH_API_TOKEN into workspace .env (no stdout secret).

Reads (first hit):
  - --token argument
  - stdin (one line)
  - env CLOUDFLARE_LOGPUSH_API_TOKEN_CLIPBOARD (optional)

  py scripts/sync_cloudflare_logpush_token_to_env_v1.py --token cfut_...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
KEY = "CLOUDFLARE_LOGPUSH_API_TOKEN"


def _norm(token: str) -> str:
    return token.strip().strip("<>").strip('"').strip("'")


def _upsert(path: Path, token: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    out: list[str] = []
    for ln in lines:
        if ln.strip().startswith(f"{KEY}="):
            continue
        out.append(ln)
    while out and not out[-1].strip():
        out.pop()
    if out:
        out.append("")
    out.append("# Turnstile Logpush (Account Logs Edit + Workers R2 Edit)")
    out.append(f"{KEY}={token}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--token", default="", help="cfut_... token value")
    args = ap.parse_args()
    import os

    raw = args.token.strip()
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
    if not raw:
        raw = os.environ.get("CLOUDFLARE_LOGPUSH_API_TOKEN_CLIPBOARD", "").strip()
    token = _norm(raw)
    if not token.startswith("cfut_"):
        print("sync_logpush_token: expected cfut_ prefix", file=sys.stderr)
        return 1
    _upsert(ENV_PATH, token)
    print(f"sync_logpush_token: ok key={KEY} path={ENV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
