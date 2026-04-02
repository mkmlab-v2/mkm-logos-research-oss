#!/usr/bin/env python3
"""Send Slack alert when all-green Slack delivery becomes stale."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = ROOT / ".env"

DEFAULT_INPUT = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "all_green_slack_delivery_check_latest.json"
DEFAULT_OUT_LATEST = ROOT / "docs" / "final" / "artifacts" / "all_green_stale_alert_latest.json"
DEFAULT_LOG_JSONL = ROOT / "docs" / "final" / "artifacts" / "all_green_stale_alert_log.jsonl"


def _load_env_from_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k in os.environ:
            continue
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
            v = v[1:-1]
        os.environ[k] = v


def _safe_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _webhook_url() -> str:
    return (
        os.getenv("ALL_GREEN_STALE_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("ALL_GREEN_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("FACT_SAFE_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    )


def _mask(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 12:
        return "***"
    return url[:6] + "***" + url[-6:]


def _append_log(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def _post(webhook: str, text: str) -> None:
    payload = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(webhook, data=payload, method="POST", headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=15) as resp:
            _ = resp.read()
    except error.URLError as exc:
        raise RuntimeError(f"Slack webhook request failed: {exc}") from exc


def main() -> int:
    p = argparse.ArgumentParser(description="Send stale Slack delivery alert")
    p.add_argument("--input", default=str(DEFAULT_INPUT))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--live", action="store_true")
    args = p.parse_args()

    _load_env_from_dotenv(DOTENV_PATH)
    doc = _safe_json(Path(args.input))
    stale = bool(doc.get("success_stale"))
    age = doc.get("latest_success_age_hours")
    max_age = doc.get("max_success_age_hours")
    checked_at = doc.get("checked_at_utc")

    record: Dict[str, Any] = {
        "schema": "all_green_stale_alert_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(Path(args.input).resolve()),
        "success_stale": stale,
        "latest_success_age_hours": age,
        "max_success_age_hours": max_age,
        "checked_at_utc": checked_at,
        "dry_run": True,
        "webhook_sent": False,
        "webhook_url_masked": "",
        "reason": "not_stale",
    }

    if not stale:
        DEFAULT_OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_log(DEFAULT_LOG_JSONL, record)
        print("[all-green-stale-alert] skip: not stale")
        return 0

    # stale=True path
    text = (
        ":warning: *ALL-GREEN SLACK DELIVERY STALE*\n"
        f"- checked_at_utc: {checked_at}\n"
        f"- latest_success_age_hours: {age}\n"
        f"- max_success_age_hours: {max_age}\n"
        "- action: verify webhook/network/runner health"
    )
    webhook = _webhook_url()
    send_live = bool(args.live) and (not args.dry_run)
    record["dry_run"] = not send_live
    record["webhook_url_masked"] = _mask(webhook)
    record["reason"] = "stale_detected"

    if not send_live:
        DEFAULT_OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_log(DEFAULT_LOG_JSONL, record)
        print("[all-green-stale-alert] dry-run: not sending")
        return 0

    if not webhook:
        raise SystemExit("Slack webhook URL not set for stale alert")

    _post(webhook, text)
    record["webhook_sent"] = True
    DEFAULT_OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(DEFAULT_LOG_JSONL, record)
    print("[all-green-stale-alert] sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

