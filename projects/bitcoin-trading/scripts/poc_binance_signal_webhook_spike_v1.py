#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PoC: single POST to Binance Global USDⓈ-M Futures Signal Bot webhook URL (from Binance UI).

NOT production wiring. Does not touch start_24h_daemon / PM2 / ENABLE_TRADING.

Official payload shape MUST be taken from Binance docs / Signal Bot UI — replace
docs/final/artifacts/examples/poc_binance_signal_webhook_payload_v1.example.json
before a real test. This script only sends bytes you give it.

Env (secrets never printed):
  BINANCE_USDM_SIGNAL_WEBHOOK_URL — full HTTPS URL (local .env only).

Usage:
  py projects/bitcoin-trading/scripts/poc_binance_signal_webhook_spike_v1.py --dry-run \\
    --payload-file docs/final/artifacts/examples/poc_binance_signal_webhook_payload_v1.example.json

  py projects/bitcoin-trading/scripts/poc_binance_signal_webhook_spike_v1.py \\
    --payload-file path/to/payload.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
import urllib.request
from urllib.parse import urlparse
from urllib.request import Request


DEFAULT_URL_ENV = "BINANCE_USDM_SIGNAL_WEBHOOK_URL"
DEFAULT_SUMMARY = Path("reports/poc_binance_signal_webhook/run_summary_latest.json")


def redact_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
        if not p.scheme or not p.netloc:
            return "(invalid-url)"
        return f"{p.scheme}://{p.netloc}/…"
    except Exception:
        return "(invalid-url)"


def optional_signature_headers(_body: bytes, _secret: str | None) -> dict[str, str]:
    """Reserved: if Binance documents HMAC/signature headers, add here — do not guess."""
    return {}


def run_post(url: str, body: bytes, timeout: float, retries: int) -> tuple[int | None, str | None, str | None]:
    last_err: str | None = None
    secret = (os.environ.get("BINANCE_USDM_SIGNAL_WEBHOOK_SECRET") or "").strip() or None
    extra = optional_signature_headers(body, secret)
    headers = {"Content-Type": "application/json", "User-Agent": "MKM-poc-binance-signal-webhook-spike-v1"}
    headers.update(extra)

    for attempt in range(max(1, retries + 1)):
        try:
            req = Request(url, data=body, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(4096)
                text = raw.decode("utf-8", errors="replace")[:2048]
                return resp.status, text, None
        except HTTPError as e:
            chunk = e.read(2048).decode("utf-8", errors="replace") if e.fp else ""
            return e.code, chunk[:2048], str(e)
        except (URLError, OSError, TimeoutError) as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(0.5)
                continue
            return None, None, last_err
    return None, None, last_err


def write_summary(
    path: Path,
    *,
    ok: bool,
    host_redacted: str,
    http_status: int | None,
    response_snippet: str | None,
    error: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "poc_binance_signal_webhook_spike_summary_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "target_host_redacted": host_redacted,
        "http_status": http_status,
        "response_snippet": response_snippet,
        "error": error,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="PoC: POST JSON to Binance USD-M Signal Bot webhook (isolated).")
    p.add_argument("--dry-run", action="store_true", help="Validate payload JSON only; no HTTP.")
    p.add_argument("--url-env", default=DEFAULT_URL_ENV, help=f"Env var for webhook URL (default {DEFAULT_URL_ENV}).")
    p.add_argument("--payload-file", required=True, type=Path, help="JSON file body to POST as UTF-8 bytes.")
    p.add_argument("--timeout", type=float, default=30.0, help="Per-attempt timeout seconds.")
    p.add_argument("--retries", type=int, default=0, help="Extra retries after first failure (network errors).")
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_SUMMARY,
        help="Write run summary JSON here (no secrets).",
    )
    args = p.parse_args(argv)

    if not args.payload_file.is_file():
        print(f"Missing payload file: {args.payload_file}", file=sys.stderr)
        return 2

    raw = args.payload_file.read_bytes()
    try:
        json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in payload file: {e}", file=sys.stderr)
        return 2

    url = (os.environ.get(args.url_env) or "").strip()
    host_r = redact_url(url) if url else "(no-url)"

    if args.dry_run:
        print(f"[dry-run] payload OK bytes={len(raw)} url_env={args.url_env} target={host_r}")
        write_summary(
            args.out,
            ok=True,
            host_redacted=host_r,
            http_status=None,
            response_snippet=None,
            error=None,
        )
        return 0

    if not url:
        print(f"Set {args.url_env} in .env (or process env) for live POST.", file=sys.stderr)
        write_summary(args.out, ok=False, host_redacted=host_r, http_status=None, response_snippet=None, error="missing_url")
        return 1

    status, snippet, err = run_post(url, raw, args.timeout, args.retries)
    ok = status is not None and 200 <= status < 300
    write_summary(
        args.out,
        ok=ok,
        host_redacted=host_r,
        http_status=status,
        response_snippet=snippet,
        error=err,
    )
    if ok:
        print(f"[ok] http_status={status} target={host_r} summary={args.out}")
        return 0
    print(f"[fail] http_status={status} err={err} target={host_r} summary={args.out}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
