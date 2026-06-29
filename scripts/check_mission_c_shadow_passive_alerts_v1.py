#!/usr/bin/env python3
"""[HYPO] Mission C shadow passive alerts — observation / human-review milestones only.

Never promotes Track A or live routing. Optional webhook/Telegram on milestone or regression.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPS = ROOT / "reports/mission_c_shadow_ops_status_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/mission_c_shadow_passive_alerts_v1_latest.json"
DEFAULT_STATE = ROOT / "reports/mission_c_shadow_alert_notify_state_v1.json"
SCHEMA = "mission_c_shadow_passive_alerts_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _webhook_url(cli: str) -> str:
    u = cli.strip()
    if u:
        return u
    u = os.getenv("MISSION_C_SHADOW_ALERT_WEBHOOK_URL", "").strip()
    if u:
        return u
    return os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()


def _post_json(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
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
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    req = request.Request(base, data=payload, method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:  # nosec B310
            return True, f"http_{resp.status}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def evaluate_alerts(ops: dict[str, Any]) -> list[dict[str, Any]]:
    gates = ops.get("gates") if isinstance(ops.get("gates"), dict) else {}
    strict = bool(gates.get("strict_passed"))
    streak = int(gates.get("strict_pass_streak") or 0)
    required = int(gates.get("strict_streak_required") or 5)
    auto_ready = bool(gates.get("auto_promote_ready"))
    outcome = str(gates.get("outcome_class") or "unknown")
    digest = ops.get("telegram_digest_block") if isinstance(ops.get("telegram_digest_block"), dict) else {}
    one_liner = str(digest.get("one_liner") or "")

    alerts: list[dict[str, Any]] = []

    if auto_ready or streak >= required:
        alerts.append(
            {
                "alert_id": "MISSION_C_STREAK_MILESTONE",
                "severity": "milestone",
                "passed": True,
                "message": (
                    f"Mission C shadow streak {streak}/{required} — human review candidate only "
                    "(no auto Track A/live)."
                ),
                "notify": True,
            }
        )
    elif not strict:
        alerts.append(
            {
                "alert_id": "MISSION_C_STRICT_FAIL",
                "severity": "warning",
                "passed": False,
                "message": f"Mission C shadow strict FAIL · outcome={outcome}",
                "notify": True,
            }
        )
    else:
        alerts.append(
            {
                "alert_id": "MISSION_C_OBSERVE",
                "severity": "info",
                "passed": True,
                "message": one_liner or f"Mission C shadow observe · streak {streak}/{required}",
                "notify": False,
            }
        )

    return alerts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops-status-json", type=Path, default=DEFAULT_OPS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--webhook-url", default="")
    ap.add_argument("--skip-webhook", action="store_true")
    ap.add_argument("--skip-telegram", action="store_true")
    args = ap.parse_args(argv)

    ops = _load(args.ops_status_json)
    if not ops:
        print(f"missing ops status: {args.ops_status_json}", file=sys.stderr)
        return 2

    alerts = evaluate_alerts(ops)
    notify_alerts = [a for a in alerts if a.get("notify")]
    all_pass = all(bool(a.get("passed")) for a in alerts)

    state = _load(args.state_json) or {}
    last_key = str(state.get("last_notify_key") or "")
    notify_key = "|".join(
        f"{a['alert_id']}:{a.get('severity')}" for a in notify_alerts
    ) + f"|streak={ops.get('gates', {}).get('strict_pass_streak')}"

    webhook_result = None
    telegram_result = None
    should_notify = bool(notify_alerts) and notify_key != last_key

    if should_notify and not args.skip_webhook:
        url = _webhook_url(args.webhook_url)
        if url:
            payload = {
                "schema": "mission_c_shadow_alert_v1",
                "ts_utc": _utc_now(),
                "research_only": True,
                "alerts": notify_alerts,
                "gates": ops.get("gates"),
                "operator_posture": ops.get("operator_posture"),
                "note": "Human review only; no auto promote.",
            }
            ok, detail = _post_json(url, payload)
            webhook_result = {"ok": ok, "detail": detail, "url_set": True}
            if ok:
                state["last_notify_key"] = notify_key
        else:
            webhook_result = {"ok": False, "detail": "no_webhook_url", "url_set": False}

    if should_notify and not args.skip_telegram:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if token and chat and notify_alerts:
            lines = ["[HYPO] Mission C shadow"]
            for a in notify_alerts:
                lines.append(str(a.get("message")))
            lines.append("research_only · no Track A/live auto merge")
            ok, detail = _send_telegram(token, chat, "\n".join(lines))
            telegram_result = {"ok": ok, "detail": detail}

    doc = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "all_alerts_passed": all_pass,
        "alerts": alerts,
        "ops_status_json": str(args.ops_status_json).replace("\\", "/"),
        "notify_attempted": should_notify,
        "webhook": webhook_result,
        "telegram": telegram_result,
        "reproducible_command": "py scripts/check_mission_c_shadow_passive_alerts_v1.py",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if webhook_result and webhook_result.get("ok"):
        args.state_json.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at_utc"] = _utc_now()
        args.state_json.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {args.output.resolve()} "
        f"pass={all_pass} notify={should_notify} alerts={len(alerts)}"
    )
    return 0 if all_pass or not notify_alerts else 1


if __name__ == "__main__":
    raise SystemExit(main())
