#!/usr/bin/env python3
"""Optional webhook when SANDBOX watchlist or early_watchlist has candidates."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WATCHLIST = ROOT / "reports/sandbox_prophecy_watchlist_v1_latest.json"
DEFAULT_DASHBOARD = ROOT / "reports/sandbox_prophecy_ops_dashboard_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_watchlist_webhook_dispatch_v1_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _resolve_webhook(primary_env: str, fallback_env: str, override: str) -> str:
    if override.strip():
        return override.strip()
    return (os.environ.get(primary_env) or os.environ.get(fallback_env) or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--watchlist-json", type=Path, default=DEFAULT_WATCHLIST)
    ap.add_argument("--dashboard-json", type=Path, default=DEFAULT_DASHBOARD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="SANDBOX_PROPHECY_WATCHLIST_WEBHOOK_URL")
    ap.add_argument("--webhook-fallback-env", type=str, default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--webhook-url", type=str, default="")
    ap.add_argument(
        "--include-early",
        action="store_true",
        default=True,
        help="Also dispatch when early_candidates non-empty (default on).",
    )
    ap.add_argument("--no-include-early", action="store_false", dest="include_early")
    args = ap.parse_args()

    wl = _read_json(args.watchlist_json)
    dash = _read_json(args.dashboard_json)
    full = [c for c in (wl.get("candidates") or []) if isinstance(c, dict)]
    early = [c for c in (wl.get("early_candidates") or []) if isinstance(c, dict)]
    trigger_rows = full + (early if args.include_early else [])
    webhook = _resolve_webhook(args.webhook_env, args.webhook_fallback_env, args.webhook_url)

    dispatch_status = "skipped_no_webhook"
    http_status: int | None = None
    if webhook and trigger_rows:
        body = {
            "source": "sandbox_prophecy_watchlist_webhook_v1",
            "generated_at_utc": _iso_now(),
            "hypothesis_tier": "SANDBOX",
            "research_only": True,
            "n_full_watchlist": len(full),
            "n_early_watchlist": len(early),
            "candidates": full[:10],
            "early_candidates": early[:10] if args.include_early else [],
            "dashboard": {
                "max_calendar_days": dash.get("max_calendar_days"),
                "health_ok": dash.get("health_ok"),
            },
        }
        req = request.Request(
            webhook,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as resp:
                http_status = resp.status
            dispatch_status = "posted"
        except error.HTTPError as e:
            http_status = e.code
            dispatch_status = f"http_error_{e.code}"
        except error.URLError as e:
            dispatch_status = f"url_error_{e.reason}"
    elif not trigger_rows:
        dispatch_status = "skipped_no_candidates"

    out = {
        "schema": "sandbox_prophecy_watchlist_webhook_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "dispatch_status": dispatch_status,
        "http_status": http_status,
        "webhook_configured": bool(webhook),
        "n_trigger_rows": len(trigger_rows),
        "include_early": args.include_early,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output_json.resolve()} status={dispatch_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
