#!/usr/bin/env python3
"""Webhook when SANDBOX watchlist calendar gate opens (days_until_watchlist_eligible == 0)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACCUMULATION = ROOT / "reports/sandbox_prophecy_accumulation_status_v1_latest.json"
DEFAULT_WATCHLIST = ROOT / "reports/sandbox_prophecy_watchlist_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_accumulation_gate_webhook_dispatch_v1_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--accumulation-json", type=Path, default=DEFAULT_ACCUMULATION)
    ap.add_argument("--watchlist-json", type=Path, default=DEFAULT_WATCHLIST)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="SANDBOX_PROPHECY_ACCUMULATION_WEBHOOK_URL")
    ap.add_argument("--webhook-fallback-env", type=str, default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--webhook-url", type=str, default="")
    ap.add_argument(
        "--notify-one-day-left",
        action="store_true",
        help="Also POST when days_until_watchlist_eligible==1 (pre-gate heads-up).",
    )
    args = ap.parse_args()

    acc = _read_json(args.accumulation_json)
    wl = _read_json(args.watchlist_json)
    gate_open = bool(acc.get("watchlist_gate_open"))
    days_left = int(acc.get("days_until_watchlist_eligible") or 99)
    pre_gate = args.notify_one_day_left and days_left == 1 and not gate_open
    should = gate_open or days_left <= 0 or pre_gate

    webhook = (args.webhook_url or "").strip() or (
        os.environ.get(args.webhook_env) or os.environ.get(args.webhook_fallback_env) or ""
    ).strip()

    dispatch_status = "skipped_gate_not_open"
    http_status: int | None = None
    if should and webhook:
        body = {
            "source": "sandbox_prophecy_accumulation_gate_webhook_v1",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hypothesis_tier": "SANDBOX",
            "research_only": True,
            "watchlist_gate_open": gate_open,
            "days_until_watchlist_eligible": days_left,
            "n_full_watchlist": len(wl.get("candidates") or []),
            "n_early_watchlist": len(wl.get("early_candidates") or []),
            "pre_gate_heads_up": pre_gate,
            "next_milestone_ko": acc.get("next_milestone_ko"),
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
    elif should:
        dispatch_status = "skipped_no_webhook"
    elif not webhook:
        dispatch_status = "skipped_no_webhook"

    out = {
        "schema": "sandbox_prophecy_accumulation_gate_webhook_dispatch_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dispatch_status": dispatch_status,
        "http_status": http_status,
        "webhook_configured": bool(webhook),
        "watchlist_gate_open": gate_open,
        "days_until_watchlist_eligible": days_left,
        "pre_gate_heads_up": pre_gate,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output_json.resolve()} status={dispatch_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
