#!/usr/bin/env python3
"""Track consecutive degraded hit-rate paths (proxy / eval_missing) and optional webhook + strict exit.

Reads docs/final/artifacts/prophecy_health_status_latest.json (run after build_prophecy_health_status_v1.py).
Persists docs/final/artifacts/prophecy_proxy_streak_state_v1.json.

Calendar-day rule: each UTC calendar day can add at most one increment to the streak (daily chain may re-run).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEALTH = ROOT / "docs" / "final" / "artifacts" / "prophecy_health_status_latest.json"
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_proxy_streak_state_v1.json"
DEFAULT_RESULT = ROOT / "docs" / "final" / "artifacts" / "prophecy_proxy_streak_gate_result_latest.json"
SCHEMA_STATE = "prophecy_proxy_streak_state_v1"
SCHEMA_RESULT = "prophecy_proxy_streak_gate_result_v1"


def _utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:  # nosec - controlled webhook call
            return True, f"http_{resp.status}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def _rel_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _degraded_from_health(health: dict[str, Any]) -> tuple[bool, str]:
    if not health:
        return True, "health_missing"
    summ = health.get("hit_rate_eval_summary") if isinstance(health.get("hit_rate_eval_summary"), dict) else {}
    path = str(summ.get("operational_path") or "")
    if path in ("proxy", "eval_missing"):
        return True, path
    return False, path


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--health-json", type=Path, default=DEFAULT_HEALTH)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--result-json", type=Path, default=DEFAULT_RESULT)
    ap.add_argument("--threshold", type=int, default=0, help="0 = use env MKM_PROPHECY_PROXY_STREAK_THRESHOLD or 3")
    ap.add_argument("--webhook-url", type=str, default="", help="Override; else MKM_PROPHECY_ALERT_WEBHOOK_URL or OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--dry-run", action="store_true", help="No webhook POST; still writes state/result")
    ap.add_argument("--strict-exit", action="store_true", help="Exit 2 when streak >= threshold (gate breach)")
    ap.add_argument("--patch-health", dest="patch_health", action="store_true", default=True)
    ap.add_argument("--no-patch-health", dest="patch_health", action="store_false", help="Do not merge proxy_streak into health JSON")
    args = ap.parse_args(argv)

    threshold = args.threshold or int(os.getenv("MKM_PROPHECY_PROXY_STREAK_THRESHOLD", "3").strip() or "3")
    if threshold < 1:
        threshold = 3

    strict = args.strict_exit or os.getenv("MKM_PROPHECY_PROXY_STREAK_STRICT_EXIT", "").strip() in (
        "1",
        "true",
        "TRUE",
        "yes",
    )

    health = _read_json(args.health_json)
    if not args.health_json.is_file():
        degraded, op_path = True, "health_missing"
    else:
        degraded, op_path = _degraded_from_health(health)

    prev = _read_json(args.state_json)
    if prev.get("schema") != SCHEMA_STATE:
        prev = {}

    today = _utc_date_str()
    prev_days = int(prev.get("consecutive_degraded_days") or 0)
    prev_inc_date = str(prev.get("last_increment_calendar_date_utc") or "")

    consecutive = prev_days
    if degraded:
        if prev_inc_date != today:
            consecutive = prev_days + 1
    else:
        consecutive = 0

    breach = consecutive >= threshold

    webhook_url = (
        args.webhook_url.strip()
        or os.getenv("MKM_PROPHECY_ALERT_WEBHOOK_URL", "").strip()
        or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
    )

    last_webhook_date = str(prev.get("last_webhook_calendar_date_utc") or "")
    should_webhook = breach and bool(webhook_url) and last_webhook_date != today
    dispatch_ok = False
    dispatch_result = "skipped"

    payload = {
        "schema": "prophecy_proxy_streak_alert_v1",
        "title": "B-track prophecy hit-rate degraded (proxy or eval_missing)",
        "consecutive_degraded_days": consecutive,
        "threshold": threshold,
        "operational_path": op_path,
        "health_json": _rel_to_root(args.health_json),
        "generated_at_utc": _utc_now_iso(),
    }

    new_wh = last_webhook_date
    if should_webhook and not args.dry_run:
        dispatch_ok, dispatch_result = _post_webhook(webhook_url, payload)
        if dispatch_ok:
            new_wh = today
    elif should_webhook and args.dry_run:
        dispatch_result = "dry_run"
    elif breach and not webhook_url:
        dispatch_result = "no_webhook_configured"

    new_state: dict[str, Any] = {
        "schema": SCHEMA_STATE,
        "version": "1.0.0",
        "updated_at_utc": _utc_now_iso(),
        "consecutive_degraded_days": consecutive,
        "last_increment_calendar_date_utc": today if degraded else None,
        "last_operational_path": op_path,
        "last_degraded": degraded,
        "streak_breach": breach,
        "threshold": threshold,
        "last_webhook_calendar_date_utc": new_wh,
    }

    args.state_json.parent.mkdir(parents=True, exist_ok=True)
    args.state_json.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result_doc: dict[str, Any] = {
        "schema": SCHEMA_RESULT,
        "version": "1.0.0",
        "generated_at_utc": _utc_now_iso(),
        "degraded": degraded,
        "operational_path": op_path,
        "consecutive_degraded_days": consecutive,
        "threshold": threshold,
        "streak_breach": breach,
        "webhook_configured": bool(webhook_url),
        "webhook_dispatched": dispatch_ok,
        "dispatch_result": dispatch_result,
        "strict_exit_would_trigger": bool(breach and strict),
    }
    args.result_json.parent.mkdir(parents=True, exist_ok=True)
    args.result_json.write_text(json.dumps(result_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.patch_health and health:
        health["proxy_streak"] = {
            "consecutive_degraded_days": consecutive,
            "threshold": threshold,
            "streak_breach": breach,
            "last_check_utc": _utc_now_iso(),
            "state_pointer": str(args.state_json.relative_to(ROOT)),
            "gate_result_pointer": str(args.result_json.relative_to(ROOT)),
        }
        args.health_json.parent.mkdir(parents=True, exist_ok=True)
        args.health_json.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "consecutive_degraded_days": consecutive,
                "streak_breach": breach,
                "dispatch_result": dispatch_result,
            },
            ensure_ascii=False,
        )
    )

    if breach and strict:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
