#!/usr/bin/env python3
"""Send readiness alert when governance status is not READY."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_READINESS = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_governance_readiness_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_readiness_alert_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:  # nosec - controlled webhook call
            return True, f"http_{resp.status}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=DEFAULT_READINESS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-url", type=str, default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    readiness = _read_json(args.readiness_json)
    status = str(readiness.get("status") or "UNKNOWN")
    reasons = readiness.get("reasons") if isinstance(readiness.get("reasons"), list) else []

    webhook_url = args.webhook_url.strip() or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
    should_alert = status != "READY"
    dispatched = False
    dispatch_result = "skipped"

    payload = {
        "schema": "layer1_layer5_readiness_alert_v1",
        "status": status,
        "reasons": reasons,
        "source": str(args.readiness_json).replace("\\", "/"),
    }

    if should_alert and webhook_url and not args.dry_run:
        dispatched, dispatch_result = _post_webhook(webhook_url, payload)
    elif should_alert and not webhook_url:
        dispatch_result = "no_webhook_configured"
    elif should_alert and args.dry_run:
        dispatch_result = "dry_run"

    out = {
        "schema": "layer1_layer5_readiness_alert_result_v1",
        "readiness_status": status,
        "should_alert": should_alert,
        "webhook_configured": bool(webhook_url),
        "dispatched": dispatched,
        "dispatch_result": dispatch_result,
        "payload_preview": payload,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "should_alert": should_alert, "dispatch_result": dispatch_result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
