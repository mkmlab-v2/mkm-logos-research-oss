#!/usr/bin/env python3
"""Build threshold switch review packet and optional ready alert (B-track)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _dispatch_webhook(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            code = int(resp.getcode())
        return {"status": "sent", "http_status": code}
    except (error.URLError, TimeoutError) as exc:
        return {"status": "failed", "error": str(exc)}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_weekly = root / "docs" / "final" / "artifacts" / "chronicle_human_gate_weekly_report_latest.json"
    default_thresholds = root / "docs" / "final" / "artifacts" / "chronicle_history_news_weekly_alert_thresholds_v1.json"
    default_p2 = root / "docs" / "final" / "artifacts" / "btrack_external_recon_p2_guardrail_result_latest.json"
    default_out = root / "docs" / "final" / "artifacts" / "chronicle_threshold_switch_review_packet_latest.json"

    ap = argparse.ArgumentParser(description="Build chronicle threshold switch review packet.")
    ap.add_argument("--weekly-report-json", default=str(default_weekly))
    ap.add_argument("--thresholds-json", default=str(default_thresholds))
    ap.add_argument("--p2-guardrail-json", default=str(default_p2))
    ap.add_argument("--output-json", default=str(default_out))
    ap.add_argument("--webhook-env", default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--force-ready", action="store_true")
    ap.add_argument("--dry-run-webhook", action="store_true")
    args = ap.parse_args()

    now = _iso_now()
    weekly = _read_json(Path(args.weekly_report_json))
    thresholds = _read_json(Path(args.thresholds_json))
    p2 = _read_json(Path(args.p2_guardrail_json))

    readiness = str(weekly.get("readiness_for_threshold_switch", "not_ready"))
    recommendation = str(weekly.get("threshold_switch_recommendation", "keep_shadow_compare_until_more_data"))
    if args.force_ready:
        readiness = "ready"
        recommendation = "consider_threshold_switch_review"
    current_thresholds = {
        "warning": thresholds.get("warning", {}),
        "critical": thresholds.get("critical", {}),
    }
    proposed_shadow = (
        (p2.get("threshold_tuning_proposal") or {}).get("proposed_shadow_only", {})
        if isinstance(p2.get("threshold_tuning_proposal"), dict)
        else {}
    )

    packet = {
        "schema": "chronicle_threshold_switch_review_packet_v1",
        "generated_at_utc": now,
        "source_track": "B",
        "governance_state": "S1_SHADOW",
        "observation_mode": "KEEP_OBSERVATION_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "readiness_for_threshold_switch": readiness,
        "threshold_switch_recommendation": recommendation,
        "weekly_report_ref": str(Path(args.weekly_report_json)),
        "comparison": {
            "current_thresholds": current_thresholds,
            "proposed_shadow_only": proposed_shadow,
        },
        "review_required": readiness == "ready",
        "rehearsal": {
            "force_ready": bool(args.force_ready),
            "dry_run_webhook": bool(args.dry_run_webhook),
        },
    }

    dispatch: dict[str, Any]
    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    if readiness == "ready" and webhook and args.dry_run_webhook:
        dispatch = {"status": "skipped", "reason": "dry_run_webhook"}
    elif readiness == "ready" and webhook:
        payload = {
            "source": "chronicle_threshold_switch_review_packet_v1",
            "event": "threshold_switch_ready",
            "generated_at_utc": now,
            "readiness_for_threshold_switch": readiness,
            "threshold_switch_recommendation": recommendation,
            "packet_path": str(Path(args.output_json)),
        }
        dispatch = _dispatch_webhook(webhook, payload)
    elif readiness == "ready" and not webhook:
        dispatch = {"status": "skipped", "reason": "webhook_not_configured"}
    else:
        dispatch = {"status": "skipped", "reason": "not_ready"}

    packet["ready_event_dispatch"] = dispatch
    Path(args.output_json).write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
