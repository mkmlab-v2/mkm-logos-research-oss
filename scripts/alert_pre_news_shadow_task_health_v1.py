#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit alert artifact when pre-news shadow task health is unhealthy.")
    ap.add_argument(
        "--health-json",
        type=Path,
        default=Path("docs/final/artifacts/pre_news_shadow_task_health_latest.json"),
    )
    ap.add_argument(
        "--out-alert-json",
        type=Path,
        default=Path("docs/final/artifacts/pre_news_shadow_task_health_alert_latest.json"),
    )
    ap.add_argument(
        "--append-log-jsonl",
        type=Path,
        default=Path("reports/pre_news_shadow_task_health_alert_log.jsonl"),
    )
    args = ap.parse_args()

    health_path = _resolve(args.health_json)
    out_path = _resolve(args.out_alert_json)
    log_path = _resolve(args.append_log_jsonl)

    health = _load(health_path)
    healthy = bool(health.get("healthy", False))
    has_alert = not healthy
    webhook_url = os.getenv("MKM_PRE_NEWS_SHADOW_ALERT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or ""
    notified = False
    notify_status = "skipped_no_alert"

    alert = {
        "schema": "pre_news_shadow_task_health_alert_v1",
        "generated_at_utc": _now(),
        "health_json": str(health_path),
        "task_name": health.get("task_name"),
        "healthy": healthy,
        "has_alert": has_alert,
        "severity": "critical" if has_alert else "none",
        "reason": None
        if healthy
        else (
            f"Task unhealthy: state={health.get('state')} "
            f"last_task_result={health.get('last_task_result')} ({health.get('last_task_result_hex')})"
        ),
        "notified": False,
        "notify_status": notify_status,
    }

    if has_alert:
        payload = {
            "event": "pre_news_shadow_task_health_alert_v1",
            "generated_at_utc": alert["generated_at_utc"],
            "task_name": alert.get("task_name"),
            "severity": alert.get("severity"),
            "reason": alert.get("reason"),
            "health_json": alert.get("health_json"),
        }
        if webhook_url:
            notified, notify_status = _post_webhook(webhook_url, payload)
            if not notified:
                notify_status = f"failed:{notify_status}"
        else:
            notify_status = "skipped_no_webhook"
    alert["notified"] = notified
    alert["notify_status"] = notify_status

    _write(out_path, alert)
    if has_alert:
        _append_jsonl(log_path, alert)

    print(f"WROTE: {out_path.resolve()}")
    if has_alert:
        print(f"APPEND: {log_path.resolve()}")
    print(f"has_alert={has_alert}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

