#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_STRICT = ART / "logos_shadow_weekly_gate_latest.json"
DEFAULT_BOOTSTRAP = ART / "logos_shadow_weekly_gate_bootstrap_latest.json"
DEFAULT_OUT = ART / "logos_shadow_alert_decision_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _post_json(url: str, payload: dict[str, Any], timeout: float = 10.0) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            code = getattr(resp, "status", 200)
            return True, f"http_{code}"
    except urllib.error.HTTPError as e:
        return False, f"http_error_{e.code}"
    except Exception as e:  # pragma: no cover - defensive
        return False, f"request_failed:{e.__class__.__name__}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Decide whether Logos shadow alert should fire.")
    ap.add_argument("--strict-gate-json", type=Path, default=DEFAULT_STRICT)
    ap.add_argument("--bootstrap-gate-json", type=Path, default=DEFAULT_BOOTSTRAP)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-url", type=str, default="")
    ap.add_argument("--send-webhook", action="store_true")
    args = ap.parse_args()

    strict_path = args.strict_gate_json if args.strict_gate_json.is_absolute() else ROOT / args.strict_gate_json
    bootstrap_path = args.bootstrap_gate_json if args.bootstrap_gate_json.is_absolute() else ROOT / args.bootstrap_gate_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not strict_path.is_file():
        raise SystemExit(f"Missing strict gate json: {strict_path}")
    if not bootstrap_path.is_file():
        raise SystemExit(f"Missing bootstrap gate json: {bootstrap_path}")

    strict = _read_json(strict_path)
    bootstrap = _read_json(bootstrap_path)
    strict_decision = str(strict.get("decision") or "UNKNOWN")
    bootstrap_decision = str(bootstrap.get("decision") or "UNKNOWN")
    mismatch = strict_decision != bootstrap_decision
    strict_hold = strict_decision == "HOLD"

    should_alert = strict_hold or mismatch
    if strict_hold:
        reason = "strict_hold"
    elif mismatch:
        reason = "strict_bootstrap_mismatch"
    else:
        reason = "no_alert_rule_match"

    payload = {
        "schema": "logos_shadow_alert_decision_v1",
        "generated_at_utc": _now(),
        "decisions": {
            "strict": strict_decision,
            "bootstrap": bootstrap_decision,
        },
        "checks": {
            "strict_hold": strict_hold,
            "strict_bootstrap_mismatch": mismatch,
        },
        "alert": {
            "should_alert": should_alert,
            "reason": reason,
        },
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
        },
        "evidence_paths": {
            "strict_gate_json": str(strict_path.resolve()),
            "bootstrap_gate_json": str(bootstrap_path.resolve()),
        },
    }

    send_req = bool(args.send_webhook)
    webhook_url = (args.webhook_url or "").strip()
    if not webhook_url:
        webhook_url = (
            os.environ.get("LOGOS_SHADOW_ALERT_WEBHOOK_URL", "").strip()
            or os.environ.get("OPS_ALARM_WEBHOOK_URL", "").strip()
        )

    webhook = {
        "requested": send_req,
        "attempted": False,
        "sent": False,
        "status": "not_requested",
    }
    if send_req and should_alert and webhook_url:
        ok, status = _post_json(webhook_url, payload)
        webhook = {
            "requested": True,
            "attempted": True,
            "sent": ok,
            "status": status,
        }
    elif send_req and should_alert and not webhook_url:
        webhook = {
            "requested": True,
            "attempted": False,
            "sent": False,
            "status": "missing_webhook_url",
        }
    elif send_req and not should_alert:
        webhook = {
            "requested": True,
            "attempted": False,
            "sent": False,
            "status": "suppressed_by_rule",
        }
    payload["webhook"] = webhook

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "should_alert": should_alert,
                "reason": reason,
                "webhook_status": webhook["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

