#!/usr/bin/env python3
"""Send Slack alert for Sentinel realtime alert (L2/high+ only).

Safety:
- Default is dry-run unless --live is passed OR SENTINEL_SLACK_LIVE env is truthy.
- Uses existing Slack webhook envs (prefers SENTINEL_SLACK_WEBHOOK_URL).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = ROOT / ".env"

DEFAULT_ALERT_JSON = ROOT / "docs" / "final" / "artifacts" / "sentinel_realtime_alert_latest.json"
DEFAULT_OUT_LATEST = ROOT / "docs" / "final" / "artifacts" / "sentinel_slack_delivery_latest.json"
DEFAULT_LOG_JSONL = ROOT / "docs" / "final" / "artifacts" / "sentinel_slack_delivery_log.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _truthy(x: str | None) -> bool:
    if x is None:
        return False
    return str(x).strip().lower() in {"1", "true", "yes", "y", "on"}


def _webhook_url() -> str:
    return (
        os.getenv("SENTINEL_SLACK_WEBHOOK_URL", "").strip()
        or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
        or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    )


def _mask_webhook(url: str) -> str:
    if not url:
        return ""
    if len(url) <= 12:
        return "***"
    return url[:6] + "***" + url[-6:]


def _safe_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _append_log(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_text(alert: Dict[str, Any]) -> str:
    sev = str(alert.get("severity") or "unknown")
    cat = str(alert.get("category") or "unknown")
    ts = str(alert.get("ts_utc") or _now_iso())
    trig = alert.get("trigger") if isinstance(alert.get("trigger"), dict) else {}
    rec = alert.get("recommended_response") if isinstance(alert.get("recommended_response"), dict) else {}
    level = str(rec.get("level") or "unknown")
    requires = bool(rec.get("requires_commander_approval"))
    corr = str(alert.get("correlation_id") or "")
    signal_key = str(trig.get("signal_key") or "unknown")
    observed = trig.get("observed_value")
    threshold = trig.get("threshold")
    lines = [
        ":rotating_light: *SENTINEL REALTIME ALERT*",
        f"- ts_utc: {ts}",
        f"- severity: {sev}",
        f"- category: {cat}",
        f"- level: {level} (requires_commander_approval={requires})",
        f"- trigger: {signal_key} observed={observed} threshold={threshold}",
    ]
    if corr:
        lines.append(f"- correlation_id: {corr}")
    snap = alert.get("context_snapshot")
    if isinstance(snap, dict):
        c2 = snap.get("c2_status")
        billing = snap.get("cost_billing_status")
        go = snap.get("a_track_go_no_go")
        lines.append(f"- snapshot: c2={c2} billing={billing} a_track={go}")
    return "\n".join(lines)


def _post_to_slack(webhook: str, text: str, timeout_s: int = 15) -> None:
    data = json.dumps({"text": text}).encode("utf-8")
    req = request.Request(
        webhook,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=timeout_s) as resp:
            _ = resp.read().decode("utf-8", errors="ignore")
            if getattr(resp, "status", 200) >= 300:
                raise RuntimeError(f"Slack webhook failed: HTTP {resp.status}")
    except error.URLError as exc:
        raise RuntimeError(f"Slack webhook request failed: {exc}") from exc


def _post_with_retry(webhook: str, text: str, timeout_s: int, max_retries: int, backoff_s: float) -> None:
    attempts = max(1, int(max_retries) + 1)
    last_err: Exception | None = None
    for i in range(attempts):
        try:
            _post_to_slack(webhook, text, timeout_s=timeout_s)
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if i >= attempts - 1:
                break
            time.sleep(max(0.0, float(backoff_s)) * (i + 1))
    if last_err is not None:
        raise RuntimeError(f"Slack send failed after retries: {last_err}") from last_err


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--alert-json", default=str(DEFAULT_ALERT_JSON))
    p.add_argument("--dry-run", action="store_true", help="Do not send webhook; write evidence only.")
    p.add_argument("--live", action="store_true", help="Force live sending even in dry-run mode.")
    p.add_argument("--timeout-s", type=int, default=15)
    p.add_argument("--max-retries", type=int, default=2)
    p.add_argument("--backoff-s", type=float, default=2.0)
    args = p.parse_args()

    _load_env_from_dotenv(DOTENV_PATH)
    live_env = _truthy(os.getenv("SENTINEL_SLACK_LIVE"))
    send_live = bool(args.live) or live_env
    if args.dry_run:
        send_live = False

    alert = _safe_json(Path(args.alert_json))
    sev = str(alert.get("severity") or "").strip().lower()
    rec = alert.get("recommended_response") if isinstance(alert.get("recommended_response"), dict) else {}
    level = str(rec.get("level") or "").strip().upper()
    eligible = (level == "L2") and (sev in {"high", "critical"})

    text = _build_text(alert)
    webhook = _webhook_url()
    record: Dict[str, Any] = {
        "schema": "sentinel_slack_delivery_v1",
        "ts_utc": _now_iso(),
        "phase": "attempt",
        "input_alert_path": str(Path(args.alert_json).resolve()),
        "eligible": eligible,
        "webhook_url_masked": _mask_webhook(webhook),
        "dry_run": not send_live,
        "webhook_sent": False,
        "final": False,
        "text_preview": text[:800],
    }

    DEFAULT_OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(DEFAULT_LOG_JSONL, record)

    if not eligible:
        record["phase"] = "final"
        record["final"] = True
        DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_log(DEFAULT_LOG_JSONL, record)
        print("[sentinel-slack] ineligible alert: skipping")
        return 0

    if not send_live:
        record["phase"] = "final"
        record["final"] = True
        DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_log(DEFAULT_LOG_JSONL, record)
        print("[sentinel-slack] dry-run: not sending Slack webhook")
        return 0

    if not webhook:
        raise SystemExit("Slack webhook URL not set (SENTINEL_SLACK_WEBHOOK_URL / OPS_ALARM_WEBHOOK_URL / SLACK_WEBHOOK_URL)")

    _post_with_retry(
        webhook=webhook,
        text=text,
        timeout_s=int(args.timeout_s),
        max_retries=int(args.max_retries),
        backoff_s=float(args.backoff_s),
    )
    record["phase"] = "final"
    record["final"] = True
    record["webhook_sent"] = True
    DEFAULT_OUT_LATEST.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_log(DEFAULT_LOG_JSONL, record)
    print("[sentinel-slack] sent Slack webhook")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

