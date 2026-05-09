#!/usr/bin/env python3
"""Post Track B cross-lens RAG alert to webhook (optional Telegram). Observation-only; non-gating.

Reads ``cross_lens_rag_alert_latest.json`` and compares ``ts_utc`` to ``cross_lens_rag_fusion_latest.json``.
If they differ, the alert file was not refreshed this fusion run (e.g. GREEN without --always-emit-alert);
notification is skipped to avoid stale YELLOW/RED noise.

Default: webhook supports full alert stream — GREEN only if ``always_emit`` or ``--include-green``.

Telegram (mobile ping) defaults to **RED only** (recommended noise floor). Set
``CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS=yellow`` (or ``--telegram-min-status yellow``) to also
ping YELLOW. GREEN never goes to Telegram.

De-dupe: same alert ts_utc is not sent twice (state file).
"""

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
DEFAULT_ALERT = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_alert_latest.json"
DEFAULT_FUSION = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_fusion_latest.json"
DEFAULT_STATE = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_alert_notify_state_latest.json"
DEFAULT_RESULT = ROOT / "docs" / "final" / "artifacts" / "cross_lens_rag_alert_notify_result_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _webhook_url(cli: str) -> str:
    u = cli.strip()
    if u:
        return u
    u = os.getenv("CROSS_LENS_RAG_ALERT_WEBHOOK_URL", "").strip()
    if u:
        return u
    return os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:  # nosec B310
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
        with request.urlopen(req, timeout=15) as resp:  # nosec B310
            if resp.status >= 300:
                body = resp.read().decode("utf-8", errors="ignore")
                return False, f"http_{resp.status}:{body[:240]}"
            return True, f"http_{resp.status}"
    except error.URLError as exc:  # pragma: no cover
        return False, f"error:{exc}"


def _telegram_notify_enabled() -> bool:
    v = os.getenv("CROSS_LENS_RAG_ALERT_TELEGRAM_NOTIFY", "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _resolve_status(alert: dict[str, Any]) -> str:
    st = str(alert.get("status") or "").strip().upper()
    if st in {"GREEN", "YELLOW", "RED"}:
        return st
    sl = alert.get("signal_light")
    if isinstance(sl, dict):
        s2 = str(sl.get("status") or "").strip().upper()
        if s2 in {"GREEN", "YELLOW", "RED"}:
            return s2
    return "UNKNOWN"


def _should_notify_payload(
    status: str,
    alert: dict[str, Any],
    *,
    include_green: bool,
) -> bool:
    if status in {"YELLOW", "RED"}:
        return True
    if status == "GREEN":
        if bool(alert.get("always_emit")):
            return True
        return bool(include_green)
    return False


def _telegram_min_status(cli_value: str | None) -> str:
    """Return ``red`` (RED-only) or ``yellow`` (YELLOW+RED). Default: red."""
    if cli_value and str(cli_value).strip():
        v = str(cli_value).strip().lower()
        if v in {"red", "yellow"}:
            return v
    raw = os.getenv("CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS", "red").strip().lower()
    if raw in {"red", "yellow"}:
        return raw
    return "red"


def _telegram_eligible_for_status(status: str, min_status: str) -> bool:
    """GREEN never; RED always; YELLOW only when min_status is yellow."""
    if status == "GREEN":
        return False
    if status == "RED":
        return True
    if status == "YELLOW":
        return min_status == "yellow"
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_RESULT)
    ap.add_argument("--webhook-url", default="", help="Override env WEBHOOK URLs.")
    ap.add_argument(
        "--include-green",
        action="store_true",
        help="Also post to webhook when status is GREEN (Telegram policy unchanged; default RED-only).",
    )
    ap.add_argument(
        "--telegram-min-status",
        choices=["red", "yellow"],
        default=None,
        help="Telegram minimum severity: red=RED-only (default), yellow=YELLOW+RED. "
        "Overrides CROSS_LENS_RAG_ALERT_TELEGRAM_MIN_STATUS.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Ignore dedupe state (resend same ts_utc).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--no-dotenv",
        action="store_true",
        help="Do not load workspace .env (tests / isolated runs).",
    )
    args = ap.parse_args()

    if not args.no_dotenv:
        _load_dotenv(DOTENV)

    alert_path = args.alert_json if args.alert_json.is_absolute() else ROOT / args.alert_json
    fusion_path = args.fusion_json if args.fusion_json.is_absolute() else ROOT / args.fusion_json
    state_path = args.state_json if args.state_json.is_absolute() else ROOT / args.state_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    fusion = _read_json(fusion_path)
    alert = _read_json(alert_path)
    state = _read_json(state_path) or {}

    result: dict[str, Any] = {
        "schema": "cross_lens_rag_alert_notify_result_v1",
        "ok": True,
        "generated_at_utc": _now_iso(),
        "alert_path": str(alert_path),
        "fusion_path": str(fusion_path),
        "notify_skipped_reason": None,
        "webhook_result": "skipped",
        "telegram_result": "skipped",
        "webhook_sent": False,
        "telegram_sent": False,
    }

    if fusion is None:
        result["ok"] = False
        result["notify_skipped_reason"] = "missing_fusion_json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if alert is None:
        result["ok"] = True
        result["notify_skipped_reason"] = "missing_alert_json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    fusion_ts = str(fusion.get("ts_utc") or "")
    alert_ts = str(alert.get("ts_utc") or "")
    if not fusion_ts or not alert_ts or fusion_ts != alert_ts:
        result["notify_skipped_reason"] = "alert_not_refreshed_this_fusion_run"
        result["fusion_ts_utc"] = fusion_ts
        result["alert_ts_utc"] = alert_ts
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    status = _resolve_status(alert)
    last_sent = str(state.get("last_notified_ts_utc") or "")
    if not args.force and alert_ts and last_sent == alert_ts:
        result["notify_skipped_reason"] = "already_notified_this_alert_ts"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if not _should_notify_payload(status, alert, include_green=bool(args.include_green)):
        result["notify_skipped_reason"] = "status_filtered"
        result["status"] = status
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    min_stat = _telegram_min_status(args.telegram_min_status)
    result["telegram_min_status"] = min_stat

    webhook = _webhook_url(args.webhook_url)
    notify_tg = _telegram_notify_enabled()
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    tg_ready = bool(notify_tg and tg_token and tg_chat)
    tg_eligible = _telegram_eligible_for_status(status, min_stat)
    tg_will_send = tg_ready and tg_eligible

    will_use_webhook = bool(webhook)
    will_use_telegram = tg_will_send

    if not will_use_webhook and not will_use_telegram:
        result["notify_skipped_reason"] = "no_delivery_channel_configured"
        result["status"] = status
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0

    envelope = {
        "schema": "cross_lens_rag_alert_notify_envelope_v1",
        "generated_at_utc": result["generated_at_utc"],
        "track": "B",
        "non_gating": True,
        "alert_ref": str(alert_path),
        "fusion_ts_utc": fusion_ts,
        "alert": alert,
    }

    delivery_ok = False

    if webhook:
        if args.dry_run:
            result["webhook_result"] = "dry_run"
        else:
            ok, msg = _post_webhook(webhook, envelope)
            result["webhook_sent"] = ok
            result["webhook_result"] = msg
            delivery_ok = delivery_ok or ok
    else:
        result["webhook_result"] = "no_webhook_configured"

    if tg_will_send:
        sl = alert.get("signal_light") if isinstance(alert.get("signal_light"), dict) else {}
        note = str(sl.get("note") or "")
        text = (
            "Cross-lens RAG alert (Track B, observation)\n"
            f"status: {status}\n"
            f"ts_utc: {alert_ts}\n"
            f"agreement: {sl.get('agreement_rate', '')}\n"
            f"{note}"
        ).strip()
        if args.dry_run:
            result["telegram_result"] = "dry_run"
        else:
            ok_t, msg_t = _send_telegram(tg_token, tg_chat, text)
            result["telegram_sent"] = ok_t
            result["telegram_result"] = msg_t
            delivery_ok = delivery_ok or ok_t
    elif not notify_tg:
        result["telegram_result"] = "telegram_notify_disabled"
    elif not tg_token or not tg_chat:
        result["telegram_result"] = "telegram_credentials_missing"
    elif not tg_eligible:
        if status == "GREEN":
            result["telegram_result"] = "skipped_non_important_for_telegram"
        else:
            result["telegram_result"] = "skipped_below_telegram_min_status"
    else:
        result["telegram_result"] = "skipped"

    if delivery_ok and not args.dry_run:
        new_state = {
            "schema": "cross_lens_rag_alert_notify_state_v1",
            "updated_at_utc": result["generated_at_utc"],
            "last_notified_ts_utc": alert_ts,
            "last_status": status,
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(new_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result["status"] = status
    result["fusion_ts_utc"] = fusion_ts
    result["alert_ts_utc"] = alert_ts
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
