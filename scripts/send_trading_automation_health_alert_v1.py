from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Send webhook alert when trading automation health is degraded.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--health-json", default="reports/trading_automation_health_latest.json")
    p.add_argument("--webhook-url", default="")
    p.add_argument("--strict", action="store_true", help="Alert when overall_ok is false only (default).")
    return p.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _read_dotenv_value(dotenv_path: Path, key: str) -> str:
    if not dotenv_path.exists():
        return ""
    prefix = f"{key}="
    for raw in dotenv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or not line.startswith(prefix):
            continue
        value = line[len(prefix):].strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value.strip()
    return ""


def _resolve_webhook(cli_webhook: str, workspace_root: Path) -> str:
    if cli_webhook.strip():
        return cli_webhook.strip()
    env_value = os.getenv("TRADING_AUTOMATION_HEALTH_WEBHOOK_URL", "").strip()
    if env_value:
        return env_value
    dotenv = workspace_root / ".env"
    dot_value = _read_dotenv_value(dotenv, "TRADING_AUTOMATION_HEALTH_WEBHOOK_URL")
    if dot_value:
        return dot_value
    fallback = os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
    if fallback:
        return fallback
    return _read_dotenv_value(dotenv, "OPS_ALARM_WEBHOOK_URL")


def _post_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8):
        return


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    health = _read_json(root / args.health_json)
    if not health:
        print("trading_health_alert_skipped=missing_health_report")
        return 0

    overall_ok = bool(health.get("overall_ok") is True)
    if overall_ok:
        print("trading_health_alert_skipped=overall_ok")
        return 0

    webhook = _resolve_webhook(args.webhook_url, root)
    if not webhook:
        print("trading_health_alert_skipped=missing_webhook")
        return 0

    payload = {
        "schema": "trading_automation_health_alert_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "alert": "TRIGGERED",
        "overall_ok": overall_ok,
        "tasks_ok": health.get("tasks_ok"),
        "security_ok": health.get("security_ok"),
        "go_no_go_ok": health.get("go_no_go_ok"),
        "go_no_go": health.get("go_no_go"),
        "security_reason": health.get("security_reason"),
        "task_health": health.get("task_health", []),
    }
    try:
        _post_webhook(webhook, payload)
        print("trading_health_alert_sent=true")
    except (urllib.error.URLError, TimeoutError):
        print("trading_health_alert_sent=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
