#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV = ROOT / ".env"
DEFAULT_STABILITY = ROOT / "docs" / "final" / "artifacts" / "mkm_global_orchestrator_go_stability_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_global_orchestrator_down_transition_alert_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if " #" in v:
            v = v.split(" #", 1)[0].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
            v = v[1:-1]
        if k and k not in os.environ:
            os.environ[k] = v


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:  # nosec B310
            return True, f"http_{resp.status}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def _send_telegram(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    base = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    )
    req = request.Request(f"{base}?{payload}", method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:  # nosec B310
            if resp.status >= 300:
                body = resp.read().decode("utf-8", errors="ignore")
                return False, f"http_{resp.status}:{body[:240]}"
            return True, f"http_{resp.status}"
    except error.URLError as exc:  # pragma: no cover
        return False, f"error:{exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Send alert on GO down-transition (GO->WATCH/HOLD).")
    ap.add_argument("--stability-json", type=Path, default=DEFAULT_STABILITY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-url", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    _load_dotenv(DOTENV)
    doc = _read_json(args.stability_json)
    transition = str(doc.get("transition") or "unknown")
    down = bool(doc.get("down_transition_detected", False))
    current = str(doc.get("current_decision") or "UNKNOWN")
    previous = str(doc.get("previous_decision") or "UNKNOWN")

    webhook_url = args.webhook_url.strip() or os.getenv("MKM_ORCHESTRATOR_DOWN_ALERT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        webhook_url = os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()

    notify_tg = os.getenv("MKM_ORCHESTRATOR_TELEGRAM_NOTIFY", "").strip().lower() in {"1", "true", "yes", "on"}
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    payload = {
        "schema": "mkm_orchestrator_down_transition_alert_v1",
        "generated_at_utc": _now(),
        "down_transition_detected": down,
        "transition": transition,
        "previous_decision": previous,
        "current_decision": current,
        "stability_ref": str(args.stability_json),
    }

    webhook_result = "skipped"
    telegram_result = "skipped"
    webhook_sent = False
    telegram_sent = False
    should_alert = down

    if should_alert and webhook_url:
        if args.dry_run:
            webhook_result = "dry_run"
        else:
            webhook_sent, webhook_result = _post_webhook(webhook_url, payload)
    elif should_alert and not webhook_url:
        webhook_result = "no_webhook_configured"

    if should_alert and notify_tg and tg_token and tg_chat:
        text = (
            "MKM Orchestrator Down Transition Alert\n"
            f"- transition: {transition}\n"
            f"- previous: {previous}\n"
            f"- current: {current}\n"
            f"- at: {payload['generated_at_utc']}"
        )
        if args.dry_run:
            telegram_result = "dry_run"
        else:
            telegram_sent, telegram_result = _send_telegram(tg_token, tg_chat, text)
    elif should_alert and notify_tg and (not tg_token or not tg_chat):
        telegram_result = "telegram_credentials_missing"
    elif should_alert and not notify_tg:
        telegram_result = "telegram_notify_disabled"

    out = {
        "schema": "mkm_orchestrator_down_transition_alert_result_v1",
        "generated_at_utc": payload["generated_at_utc"],
        "should_alert": should_alert,
        "transition": transition,
        "webhook_configured": bool(webhook_url),
        "webhook_sent": webhook_sent,
        "webhook_result": webhook_result,
        "telegram_sent": telegram_sent,
        "telegram_result": telegram_result,
        "payload_preview": payload,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "should_alert": should_alert,
                "transition": transition,
                "webhook_result": webhook_result,
                "telegram_result": telegram_result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
