#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description="Regression guard for AGCT locked baseline chain.")
    ap.add_argument("--latest-json", default="reports/agct_sigma_locked_baseline_chain_v1_latest.json")
    ap.add_argument("--baseline-json", default="reports/agct_sigma_locked_baseline_chain_v1_run1.json")
    ap.add_argument("--out", default="reports/agct_sigma_locked_baseline_regression_check_latest.json")
    ap.add_argument("--min-go-rate", type=float, default=0.25)
    ap.add_argument("--min-transition-intensity", type=float, default=0.40)
    ap.add_argument(
        "--min-trials-for-hard-enforcement",
        type=int,
        default=5,
        help="If latest repro_trials is below this, emit WARN instead of ALERT for metric/baseline gates.",
    )
    ap.add_argument("--alert-webhook-env", default="OPS_ALARM_WEBHOOK_URL")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    latest_path = (root / args.latest_json).resolve()
    baseline_path = (root / args.baseline_json).resolve()
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    status = "PASS"
    reasons: list[str] = []
    latest: dict[str, Any] = {}
    baseline: dict[str, Any] = {}

    if not latest_path.exists():
        status = "ALERT"
        reasons.append("latest_report_missing")
    else:
        latest = _read_json(latest_path)
    if not baseline_path.exists():
        status = "ALERT"
        reasons.append("baseline_report_missing")
    else:
        baseline = _read_json(baseline_path)

    latest_summary = latest.get("summary") if isinstance(latest.get("summary"), dict) else {}
    baseline_summary = baseline.get("summary") if isinstance(baseline.get("summary"), dict) else {}

    latest_chain_status = str(latest_summary.get("status") or "unknown")
    baseline_chain_status = str(baseline_summary.get("status") or "unknown")
    latest_go = _to_float(latest_summary.get("repro_go_rate_mean"))
    latest_ti = _to_float(latest_summary.get("repro_transition_intensity_mean"))
    baseline_go = _to_float(baseline_summary.get("repro_go_rate_mean"))
    baseline_ti = _to_float(baseline_summary.get("repro_transition_intensity_mean"))
    latest_inputs = latest.get("inputs") if isinstance(latest.get("inputs"), dict) else {}
    baseline_inputs = baseline.get("inputs") if isinstance(baseline.get("inputs"), dict) else {}
    latest_repro_trials = int(_to_float(latest_inputs.get("repro_trials"), 0))
    baseline_repro_trials = int(_to_float(baseline_inputs.get("repro_trials"), 0))
    hard_enforcement = latest_repro_trials >= int(args.min_trials_for_hard_enforcement)

    if latest and latest_chain_status not in {"PASS", "WARN"}:
        status = "ALERT"
        reasons.append("latest_chain_not_pass_or_warn")
    if baseline and baseline_chain_status != "PASS":
        status = "ALERT"
        reasons.append("baseline_chain_not_pass")
    metric_reasons: list[str] = []
    if latest and latest_go < float(args.min_go_rate):
        metric_reasons.append("latest_go_rate_below_floor")
    if latest and latest_ti < float(args.min_transition_intensity):
        metric_reasons.append("latest_transition_intensity_below_floor")
    if latest and baseline and latest_go < baseline_go:
        metric_reasons.append("latest_go_rate_below_baseline")
    if latest and baseline and latest_ti < baseline_ti:
        metric_reasons.append("latest_transition_intensity_below_baseline")
    if metric_reasons:
        reasons.extend(metric_reasons)
        if hard_enforcement:
            status = "ALERT"
        elif status == "PASS":
            status = "WARN"

    payload: dict[str, Any] = {
        "schema": "agct_locked_baseline_regression_check_v1",
        "generated_at_utc": _utc_now(),
        "status": status,
        "reasons": reasons,
        "latest_report": str(latest_path),
        "baseline_report": str(baseline_path),
        "floors": {
            "min_go_rate": float(args.min_go_rate),
            "min_transition_intensity": float(args.min_transition_intensity),
            "min_trials_for_hard_enforcement": int(args.min_trials_for_hard_enforcement),
        },
        "metrics": {
            "latest_chain_status": latest_chain_status,
            "baseline_chain_status": baseline_chain_status,
            "latest_go_rate": latest_go,
            "latest_transition_intensity": latest_ti,
            "baseline_go_rate": baseline_go,
            "baseline_transition_intensity": baseline_ti,
            "latest_repro_trials": latest_repro_trials,
            "baseline_repro_trials": baseline_repro_trials,
        },
        "hard_enforcement_applied": hard_enforcement,
        "alert_sent": False,
    }

    if status == "ALERT":
        webhook = os.getenv(args.alert_webhook_env, "").strip()
        if webhook:
            req_body = json.dumps(
                {
                    "event": "agct_locked_baseline_regression",
                    "kind": "warning",
                    "status": status,
                    "reasons": reasons,
                    "latest_report": str(latest_path),
                    "baseline_report": str(baseline_path),
                    "ts_utc": payload["generated_at_utc"],
                }
            ).encode("utf-8")
            req = urllib.request.Request(webhook, data=req_body, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
                    payload["alert_http_status"] = getattr(resp, "status", None)
                    payload["alert_sent"] = True
            except Exception as exc:
                payload["alert_error"] = str(exc)
        else:
            payload["alert_skipped_reason"] = "webhook_not_configured"

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} status={status}")
    return 0 if status in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

