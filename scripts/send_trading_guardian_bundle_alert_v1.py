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
    p = argparse.ArgumentParser(description="Send webhook alert when guardian bundle status is degraded.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--bundle-json", default="reports/trading_guardian_bundle_status_latest.json")
    p.add_argument("--state-json", default="reports/trading_guardian_bundle_alert_state_latest.json")
    p.add_argument("--cooldown-hours", type=float, default=0.5)
    p.add_argument("--webhook-url", default="")
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
    env_value = os.getenv("TRADING_GUARDIAN_BUNDLE_WEBHOOK_URL", "").strip()
    if env_value:
        return env_value
    dotenv = workspace_root / ".env"
    dot_value = _read_dotenv_value(dotenv, "TRADING_GUARDIAN_BUNDLE_WEBHOOK_URL")
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


def _build_dedup_key(bundle: dict[str, Any]) -> str:
    components = bundle.get("components") if isinstance(bundle.get("components"), dict) else {}
    health = components.get("trading_automation_health") if isinstance(components.get("trading_automation_health"), dict) else {}
    coverage = components.get("protective_coverage") if isinstance(components.get("protective_coverage"), dict) else {}
    pos = coverage.get("position") if isinstance(coverage.get("position"), dict) else {}
    fields = [
        str(bundle.get("status", "UNKNOWN")).upper(),
        str(health.get("go_no_go", "UNKNOWN")).upper(),
        str(coverage.get("status", "unknown")).lower(),
        str(pos.get("side", "unknown")).upper(),
    ]
    return "|".join(fields)


def _is_in_cooldown(state: dict[str, Any], dedup_key: str, cooldown_hours: float) -> bool:
    if not state or str(state.get("dedup_key", "")) != dedup_key:
        return False
    ts = str(state.get("last_sent_at_utc", "")).strip()
    if not ts:
        return False
    try:
        sent = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    elapsed_seconds = (datetime.now(timezone.utc) - sent).total_seconds()
    return elapsed_seconds < max(0.0, float(cooldown_hours)) * 3600.0


def _write_state(path: Path, dedup_key: str, bundle_status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "trading_guardian_bundle_alert_state_v1",
        "last_sent_at_utc": datetime.now(timezone.utc).isoformat(),
        "dedup_key": dedup_key,
        "bundle_status": bundle_status,
    }
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    bundle = _read_json(root / args.bundle_json)
    if not bundle:
        print("trading_guardian_bundle_alert_skipped=missing_bundle_report")
        return 0

    status = str(bundle.get("status", "UNKNOWN")).upper()
    if status == "GREEN":
        print("trading_guardian_bundle_alert_skipped=status_green")
        return 0

    state_path = root / args.state_json
    dedup_key = _build_dedup_key(bundle)
    state = _read_json(state_path)
    if _is_in_cooldown(state, dedup_key, args.cooldown_hours):
        print("trading_guardian_bundle_alert_skipped=cooldown")
        return 0

    webhook = _resolve_webhook(args.webhook_url, root)
    if not webhook:
        print("trading_guardian_bundle_alert_skipped=missing_webhook")
        return 0

    payload = {
        "schema": "trading_guardian_bundle_alert_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "alert": "TRIGGERED",
        "status": status,
        "ok": bundle.get("ok"),
        "components": bundle.get("components", {}),
    }
    try:
        _post_webhook(webhook, payload)
        _write_state(state_path, dedup_key, status)
        print("trading_guardian_bundle_alert_sent=true")
    except (urllib.error.URLError, TimeoutError):
        print("trading_guardian_bundle_alert_sent=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
