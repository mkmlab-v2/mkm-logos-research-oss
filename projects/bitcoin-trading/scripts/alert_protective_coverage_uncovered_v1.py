#!/usr/bin/env python3
"""Send webhook alert when protective coverage is uncovered."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
WS_ART = WORKSPACE_ROOT / "docs" / "final" / "artifacts"
WS_REPORTS = WORKSPACE_ROOT / "reports" / "binance_usdm_single_order"
OUT = WS_ART / "protective_coverage_alert_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write(payload: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _post(url: str, payload: dict) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=12) as resp:
            return 200 <= int(resp.status) < 300, f"http_status={resp.status}"
    except HTTPError as e:
        return False, f"http_error={e.code}"
    except (URLError, TimeoutError, OSError) as e:
        return False, f"network_error={e}"


def main() -> int:
    cov = (
        _read_json(WS_REPORTS / "protective_order_coverage_latest.json")
        or _read_json(WS_ART / "protective_order_coverage_latest.json")
        or _read_json(ART / "protective_order_coverage_latest.json")
    )
    status = str(cov.get("status") or "unknown")
    ok = bool(cov.get("ok"))
    coverage = cov.get("coverage") if isinstance(cov.get("coverage"), dict) else {}
    pside = coverage.get("position_side")
    pqty = coverage.get("position_qty")
    req_qty = coverage.get("required_qty")
    webhook = (os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()

    result = {
        "schema": "protective_coverage_alert_v1",
        "generated_at_utc": _utc_now(),
        "coverage_status": status,
        "coverage_ok": ok,
        "alert_sent": False,
        "note": None,
    }

    if status != "uncovered":
        result["note"] = "no_alert_needed"
        _write(result)
        print("no_alert_needed")
        return 0

    if not webhook:
        result["note"] = "missing_ops_alarm_webhook_url"
        _write(result)
        print("missing OPS_ALARM_WEBHOOK_URL", file=sys.stderr)
        return 1

    msg = (
        "[MKM] Protective coverage uncovered on BTCUSDT "
        f"(side={pside}, qty={pqty}, required_qty={req_qty})"
    )
    alert_payload = {
        "text": msg,
        "schema": "protective_coverage_uncovered_event_v1",
        "coverage": cov,
        "ts_utc": _utc_now(),
    }
    sent, detail = _post(webhook, alert_payload)
    result["alert_sent"] = sent
    result["note"] = detail
    _write(result)
    if sent:
        print("alert_sent")
        return 0
    print(detail, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
