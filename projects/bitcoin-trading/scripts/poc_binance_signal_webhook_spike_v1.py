#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PoC: single POST to Binance Global USDⓈ-M Futures Signal Bot webhook URL (from Binance UI).

NOT production wiring. Does not touch start_24h_daemon / PM2 / ENABLE_TRADING.

Official payload shape MUST be taken from Binance docs / Signal Bot UI — replace
docs/final/artifacts/examples/poc_binance_signal_webhook_payload_v1.example.json
before a real test. This script only sends bytes you give it.

Env (secrets never printed; resolution aligns with ``binance_client`` / §1.1.2):
  BINANCE_USDM_SIGNAL_WEBHOOK_URL — full HTTPS URL.
  BINANCE_USDM_SIGNAL_WEBHOOK_SECRET — optional body/header secret if Binance documents it.

  Priority (when BINANCE_KEY_SOURCE_MODE is unset or ``auto``):
  Security Agent (DPAPI / ``Invoke-EncryptedSecretStore.ps1``) → process env → workspace ``.env`` / cwd ``.env``.
  Override routing with BINANCE_KEY_SOURCE_MODE=dotenv_only | env_only (same as API keys).

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
from typing import Any, Optional

# Monorepo root (…/workspace): scripts/security_agent_manager.py
_SECURITY_AGENT_AVAILABLE = False
try:
    _WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(_WORKSPACE_ROOT))
    from scripts.security_agent_manager import get_security_agent

    _SECURITY_AGENT_AVAILABLE = True
except ImportError:
    _WORKSPACE_ROOT = Path(__file__).resolve().parents[3]

from urllib.error import HTTPError, URLError
import urllib.request
from urllib.parse import urlparse
from urllib.request import Request


DEFAULT_URL_ENV = "BINANCE_USDM_SIGNAL_WEBHOOK_URL"
DEFAULT_SECRET_ENV = "BINANCE_USDM_SIGNAL_WEBHOOK_SECRET"
DEFAULT_SUMMARY = Path("reports/poc_binance_signal_webhook/run_summary_latest.json")


def _credential_source_mode() -> str:
    raw = os.getenv("BINANCE_KEY_SOURCE_MODE", "auto")
    return str(raw or "auto").strip().lower()


def _read_key_from_dotenv(dotenv_path: Path, key: str) -> Optional[str]:
    """Read a single KEY=value from .env (no shell expansion)."""
    try:
        if not dotenv_path.is_file():
            return None
        prefix = f"{key}="
        for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or not line.startswith(prefix):
                continue
            value = line[len(prefix) :].strip()
            if " #" in value:
                value = value.split(" #", 1)[0].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value.strip() or None
    except OSError:
        return None
    return None


def resolve_env_var(key: str) -> str:
    """
    Resolve a secret/config env value: Security Agent → env → .env files.
    Uses BINANCE_KEY_SOURCE_MODE like binance_client (auto | dotenv_only | env_only).
    """
    mode = _credential_source_mode()
    dotenv_only = mode in ("dotenv_only", "dotenv")
    env_only = mode in ("env_only", "env")

    if _SECURITY_AGENT_AVAILABLE and not (dotenv_only or env_only):
        try:
            agent = get_security_agent()
            v = agent.get_env_var(key)
            if v and str(v).strip():
                return str(v).strip()
        except Exception:
            pass

    if not dotenv_only:
        v = os.getenv(key)
        if v and str(v).strip():
            return str(v).strip()

    if not env_only:
        for dotenv in (_WORKSPACE_ROOT / ".env", Path.cwd() / ".env"):
            got = _read_key_from_dotenv(dotenv, key)
            if got and got.strip():
                return got.strip()

    return ""


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


def run_post(
    url: str,
    body: bytes,
    timeout: float,
    retries: int,
    *,
    webhook_secret: str | None,
) -> tuple[int | None, str | None, str | None]:
    last_err: str | None = None
    secret = (webhook_secret or "").strip() or None
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
    p.add_argument("--url-env", default=DEFAULT_URL_ENV, help=f"Env var name for webhook URL (default {DEFAULT_URL_ENV}).")
    p.add_argument(
        "--secret-env",
        default=DEFAULT_SECRET_ENV,
        help=f"Env var name for optional webhook secret (default {DEFAULT_SECRET_ENV}).",
    )
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

    url = resolve_env_var(args.url_env)
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
        print(
            f"Missing {args.url_env}: set Security Agent (DPAPI), process env, or workspace/.env — "
            f"see CONSTITUTION §1.1.2 / BINANCE_KEY_SOURCE_MODE.",
            file=sys.stderr,
        )
        write_summary(args.out, ok=False, host_redacted=host_r, http_status=None, response_snippet=None, error="missing_url")
        return 1

    webhook_secret = resolve_env_var(args.secret_env) or None
    status, snippet, err = run_post(url, raw, args.timeout, args.retries, webhook_secret=webhook_secret)
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
