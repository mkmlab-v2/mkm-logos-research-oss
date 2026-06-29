#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_holdout_gate_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_explainability_holdout_alert_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _slack_webhook_body(url: str, payload: dict[str, Any]) -> bytes:
    host = url.split("://", 1)[-1].split("/", 1)[0].lower()
    if host != "hooks.slack.com":
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")
    failed = payload.get("failed_check_keys") or []
    metrics = payload.get("metrics_snapshot") or {}
    text = (
        f"[MKM] general_prophecy holdout gate: {payload.get('decision', 'UNKNOWN')}\n"
        f"profile={payload.get('profile', 'unknown')} all_pass={payload.get('all_pass', False)}\n"
        f"failed={', '.join(str(x) for x in failed) or 'none'}\n"
        f"repro={metrics.get('holdout_reproducible_evidence_rate')} "
        f"coverage={metrics.get('holdout_avg_biblical_keyword_coverage')}"
    )
    return json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")


def post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    data = _slack_webhook_body(url, payload)
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=10) as resp:  # nosec - controlled webhook call
            return True, f"http_{resp.status}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Dispatch webhook alert when holdout gate warns.")
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-url", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gate_path = args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json
    if not gate_path.is_file():
        raise SystemExit(f"Missing --gate-json: {gate_path}")
    gate = load_json(gate_path)
    decision = str(gate.get("decision", "UNKNOWN"))
    alert_needed = decision == "WARN_HOLDOUT_DRIFT_RISK"
    checks = gate.get("checks") if isinstance(gate.get("checks"), dict) else {}
    failed_check_keys = [str(k) for k, v in checks.items() if v is False]

    webhook_url = (
        args.webhook_url.strip()
        or os.getenv("MKM_GENERAL_PROPHECY_HOLDOUT_ALERT_WEBHOOK_URL", "").strip()
        or os.getenv("OPS_ALARM_WEBHOOK_URL", "").strip()
    )
    payload = {
        "schema": "general_prophecy_holdout_alert_v1",
        "generated_at_utc": utc_now(),
        "decision": decision,
        "all_pass": bool(gate.get("all_pass", False)),
        "profile": str(gate.get("profile", "unknown")),
        "thresholds": gate.get("thresholds", {}),
        "metrics_snapshot": gate.get("metrics_snapshot", {}),
        "failed_check_keys": failed_check_keys,
        "gate_json": str(gate_path).replace("\\", "/"),
    }

    dispatched = False
    dispatch_result = "not_needed"
    if alert_needed:
        if not webhook_url:
            dispatch_result = "no_webhook_configured"
        elif args.dry_run:
            dispatch_result = "dry_run"
        else:
            dispatched, dispatch_result = post_webhook(webhook_url, payload)

    out = {
        "schema": "general_prophecy_explainability_holdout_alert_result_v1",
        "generated_at_utc": utc_now(),
        "gate_json": str(gate_path).replace("\\", "/"),
        "alert_needed": alert_needed,
        "webhook_configured": bool(webhook_url),
        "webhook_dispatched": dispatched,
        "dispatch_result": dispatch_result,
        "decision": decision,
        "failed_check_keys": failed_check_keys,
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "alert_needed": alert_needed, "dispatch_result": dispatch_result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
