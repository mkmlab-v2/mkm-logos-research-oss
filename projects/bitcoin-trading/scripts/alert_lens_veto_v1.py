#!/usr/bin/env python3
"""Send webhook alerts for lens veto events and high veto-rate windows."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = line.strip()
        if not t:
            continue
        try:
            obj = json.loads(t)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _post(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=12) as resp:
            return 200 <= int(resp.status) < 300, f"http_status={resp.status}"
    except HTTPError as e:
        return False, f"http_error={e.code}"
    except (URLError, TimeoutError, OSError) as e:
        return False, f"network_error={e}"


def _read_env_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ln.startswith(f"{key}="):
            return ln.split("=", 1)[1].strip()
    return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Alert on lens veto event and veto-rate threshold.")
    ap.add_argument(
        "--events-jsonl",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/logs/lens_gate_events.jsonl"),
    )
    ap.add_argument(
        "--daily-report-json",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/docs/final/artifacts/lens_veto_daily_report_latest.json"),
    )
    ap.add_argument(
        "--state-json",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/docs/final/artifacts/lens_veto_alert_state_latest.json"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("/opt/bitcoin-trading-live/docs/final/artifacts/lens_veto_alert_latest.json"),
    )
    ap.add_argument("--veto-rate-threshold", type=float, default=0.20)
    args = ap.parse_args(argv)

    webhook = (os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()
    if not webhook:
        webhook = _read_env_value(Path("/opt/bitcoin-trading-live/.env"), "OPS_ALARM_WEBHOOK_URL")
    if not webhook:
        webhook = _read_env_value(Path("/opt/bitcoin-trading/.env"), "OPS_ALARM_WEBHOOK_URL")
    result: dict[str, Any] = {
        "schema": "lens_veto_alert_v1",
        "generated_at_utc": _utc_now(),
        "webhook_configured": bool(webhook),
        "event_alert_sent": False,
        "event_alert_note": "no_veto_event",
        "rate_alert_sent": False,
        "rate_alert_note": "below_threshold_or_missing",
    }

    state = _read_json(args.state_json)
    last_event_key = str(state.get("last_event_alert_key") or "")
    last_rate_key = str(state.get("last_rate_alert_key") or "")

    # 1) Immediate event alert: newest HOLD_LENS_VETO only.
    newest_veto: dict[str, Any] | None = None
    for row in reversed(_read_jsonl(args.events_jsonl)):
        if str(row.get("signal") or "") == "HOLD_LENS_VETO":
            newest_veto = row
            break

    next_event_key = None
    if newest_veto:
        gate = newest_veto.get("lens_gate") if isinstance(newest_veto.get("lens_gate"), dict) else {}
        next_event_key = f"{newest_veto.get('timestamp')}|{gate.get('target_before')}|{gate.get('lens_direction')}"
        result["latest_veto_event"] = newest_veto
        if next_event_key == last_event_key:
            result["event_alert_note"] = "already_alerted"
        elif webhook:
            msg = (
                "[MKM] Lens veto triggered: "
                f"target={gate.get('target_before')} blocked={gate.get('blocked')} "
                f"lens_dir={gate.get('lens_direction')} conf={gate.get('lens_confidence')} "
                f"ts={newest_veto.get('timestamp')}"
            )
            payload = {
                "text": msg,
                "schema": "lens_veto_event_alert_v1",
                "event": newest_veto,
                "ts_utc": _utc_now(),
            }
            sent, note = _post(webhook, payload)
            result["event_alert_sent"] = sent
            result["event_alert_note"] = note
            if sent:
                last_event_key = next_event_key
        else:
            result["event_alert_note"] = "missing_ops_alarm_webhook_url"

    # 2) Threshold alert: 24h veto_rate above threshold.
    daily = _read_json(args.daily_report_json)
    veto = daily.get("veto") if isinstance(daily.get("veto"), dict) else {}
    rate = float(veto.get("veto_rate") or 0.0)
    report_ts = str(daily.get("generated_at_utc") or "")
    threshold = max(0.0, float(args.veto_rate_threshold))
    next_rate_key = f"{report_ts}|{threshold}|{rate:.6f}"
    result["rate_check"] = {"veto_rate": rate, "threshold": threshold}
    if report_ts and rate >= threshold:
        if next_rate_key == last_rate_key:
            result["rate_alert_note"] = "already_alerted"
        elif webhook:
            msg = (
                "[MKM] Lens veto rate alert: "
                f"veto_rate_24h={rate:.4f} threshold={threshold:.4f} "
                f"veto_count={veto.get('veto_count')} total={daily.get('window', {}).get('events_total_window')}"
            )
            payload = {
                "text": msg,
                "schema": "lens_veto_rate_alert_v1",
                "daily_report": daily,
                "ts_utc": _utc_now(),
            }
            sent, note = _post(webhook, payload)
            result["rate_alert_sent"] = sent
            result["rate_alert_note"] = note
            if sent:
                last_rate_key = next_rate_key
        else:
            result["rate_alert_note"] = "missing_ops_alarm_webhook_url"

    new_state = {
        "schema": "lens_veto_alert_state_v1",
        "updated_at_utc": _utc_now(),
        "last_event_alert_key": last_event_key,
        "last_rate_alert_key": last_rate_key,
    }
    _write_json(args.state_json, new_state)
    _write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
