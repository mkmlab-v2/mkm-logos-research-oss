#!/usr/bin/env python3
"""Dispatch genius benchmark alert to webhook when severity is warning/critical."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_ALERT = ART / "genius_reasoning_benchmark_alert_latest.json"
DEFAULT_OUT = ART / "genius_reasoning_benchmark_alert_dispatch_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alert-json", type=Path, default=DEFAULT_ALERT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", type=str, default="OPS_ALARM_WEBHOOK_URL")
    args = ap.parse_args()

    alert_doc = _read_json(args.alert_json)
    alert = alert_doc.get("alert") if isinstance(alert_doc.get("alert"), dict) else {}
    current = alert_doc.get("current") if isinstance(alert_doc.get("current"), dict) else {}
    severity = str(alert.get("severity") or "INFO").upper()
    active = bool(alert.get("active"))
    should_dispatch = active and severity in {"WARNING", "CRITICAL"}

    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    out: dict[str, Any] = {
        "schema": "genius_reasoning_benchmark_alert_dispatch_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "alert_json": str(args.alert_json).replace("\\", "/"),
            "webhook_env": args.webhook_env,
        },
        "decision": {
            "severity": severity,
            "active": active,
            "should_dispatch": should_dispatch,
            "webhook_configured": bool(webhook),
        },
    }

    if should_dispatch and webhook:
        payload = {
            "source": "genius_reasoning_alert_v1",
            "severity": severity,
            "reasons": alert.get("reasons") or [],
            "current": {
                "benchmark_status": current.get("benchmark_status"),
                "robust_benchmark_status": current.get("robust_benchmark_status"),
                "robust_score_100": current.get("robust_score_100"),
                "calibration_gap": current.get("calibration_gap"),
                "coverage_gate_pass": current.get("coverage_gate_pass"),
            },
            "generated_at_utc": _iso_now(),
        }
        req = request.Request(
            webhook,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                status_code = int(resp.getcode())
            out["dispatch"] = {"status": "sent", "http_status": status_code}
        except (error.URLError, TimeoutError) as exc:
            out["dispatch"] = {"status": "failed", "error": str(exc)}
    elif should_dispatch and not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "alert_not_dispatchable"}

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "dispatch_status": (out.get("dispatch") or {}).get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
