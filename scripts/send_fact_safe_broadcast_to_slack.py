# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.7, K:0.5, M:0.6}
# Balance: 89
# Purpose: Send Fact-Safe broadcast summary to Slack webhook.
# Keywords: slack, webhook, broadcast, fact-safe
"""Send fact-safe broadcast summary to Slack webhook."""

from __future__ import annotations

import argparse
import json
import os
from urllib import parse
from pathlib import Path
from urllib import error, request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BROADCAST_JSON = (
    ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "briefs" / "fact_safe_multilens_broadcast_latest.json"
)
DOTENV_PATH = ROOT / ".env"
DEFAULT_STATUS_JSON = ROOT / "reports" / "constitution" / "btrack_pilot" / "fact_safe_slack_delivery_latest.json"
DEFAULT_STATUS_LOG_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "fact_safe_slack_delivery_log.jsonl"


def _safe_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def _append_status_log(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8") if not path.exists() else None
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(status, ensure_ascii=False) + "\n")


def _load_env_from_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not key:
            continue
        # Keep process env precedence and avoid overriding externally provided secrets.
        if key in os.environ:
            continue
        os.environ[key] = value


def build_slack_text(payload: dict) -> str:
    return "\n".join(
        [
            ":shield: *Fact-Safe Monthly Broadcast*",
            f"- generated_at_utc: {payload.get('ts_utc')}",
            f"- reliability_badge: {payload.get('reliability_badge')}",
            f"- high_reliability_decision: {payload.get('high_reliability_decision')}",
            f"- gate_reason: {payload.get('gate_reason')}",
            f"- net: {payload.get('net')}",
            f"- history_samples: {payload.get('history_samples')}",
            f"- history_net_delta: {payload.get('history_net_delta')}",
            (
                f"- overlap_drift_alert: {payload.get('overlap_drift_alert')} "
                f"(threshold={payload.get('overlap_drift_alert_threshold')})"
            ),
        ]
    )


def post_to_slack(webhook_url: str, text: str) -> None:
    data = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore").strip()
            if resp.status >= 300:
                raise RuntimeError(f"Slack webhook failed: HTTP {resp.status}, body={body}")
    except error.URLError as exc:
        raise RuntimeError(f"Slack webhook request failed: {exc}") from exc


def post_to_telegram(bot_token: str, chat_id: str, text: str) -> None:
    base = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = parse.urlencode({"chat_id": chat_id, "text": text})
    req = request.Request(
        f"{base}?{payload}",
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="ignore").strip()
            if resp.status >= 300:
                raise RuntimeError(f"Telegram send failed: HTTP {resp.status}, body={body}")
    except error.URLError as exc:
        raise RuntimeError(f"Telegram request failed: {exc}") from exc


def main() -> int:
    _load_env_from_dotenv(DOTENV_PATH)
    parser = argparse.ArgumentParser(description="Send Fact-Safe broadcast to Slack")
    parser.add_argument("--input", default=str(DEFAULT_BROADCAST_JSON))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status-out", default=str(DEFAULT_STATUS_JSON))
    parser.add_argument("--status-log-out", default=str(DEFAULT_STATUS_LOG_JSONL))
    parser.add_argument("--telegram-bot-token", default=os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
    parser.add_argument("--telegram-chat-id", default=os.getenv("TELEGRAM_CHAT_ID", "").strip())
    parser.add_argument(
        "--webhook-url",
        default=(
            os.getenv("FACT_SAFE_SLACK_WEBHOOK_URL", "").strip()
            or os.getenv("SLACK_WEBHOOK_URL", "").strip()
        ),
    )
    args = parser.parse_args()

    payload = _safe_json(Path(args.input))
    status_out = Path(args.status_out)
    status_log_out = Path(args.status_log_out)
    status_out.parent.mkdir(parents=True, exist_ok=True)
    status = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_path": str(Path(args.input)),
        "status": "unknown",
        "reason": "",
        "dry_run": bool(args.dry_run),
        "sent": False,
        "channel": None,
    }
    if not payload:
        print(f"WARNING: broadcast payload missing or invalid: {args.input}")
        status["status"] = "skipped"
        status["reason"] = "invalid_or_missing_payload"
        status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_status_log(status_log_out, status)
        return 0

    text = build_slack_text(payload)
    print(text)
    if args.dry_run:
        print("DRY RUN: Slack message not sent.")
        status["status"] = "skipped"
        status["reason"] = "dry_run"
        status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_status_log(status_log_out, status)
        return 0
    if not args.webhook_url:
        if args.telegram_bot_token and args.telegram_chat_id:
            post_to_telegram(args.telegram_bot_token, args.telegram_chat_id, text)
            print("Telegram message sent successfully.")
            status["status"] = "sent"
            status["reason"] = "telegram_fallback"
            status["sent"] = True
            status["channel"] = "telegram"
            status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            _append_status_log(status_log_out, status)
            return 0
        print(
            "WARNING: FACT_SAFE_SLACK_WEBHOOK_URL/SLACK_WEBHOOK_URL missing and Telegram token/chat_id missing; send skipped."
        )
        status["status"] = "skipped"
        status["reason"] = "missing_slack_and_telegram"
        status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_status_log(status_log_out, status)
        return 0

    post_to_slack(args.webhook_url, text)
    print("Slack message sent successfully.")
    status["status"] = "sent"
    status["reason"] = "ok"
    status["sent"] = True
    status["channel"] = "slack"
    status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_status_log(status_log_out, status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
