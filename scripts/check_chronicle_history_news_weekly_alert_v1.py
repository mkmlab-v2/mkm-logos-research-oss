#!/usr/bin/env python3
"""Check weekly chronicle-history-news signal eval against alert thresholds."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def _to_iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _eval_gate(
    *,
    row_count: int,
    avg_score: float,
    watch_ratio: float,
    reduce_ratio: float,
    guard_active: bool,
    gate: dict[str, Any],
    tag: str,
) -> list[str]:
    failures: list[str] = []
    if row_count < int(gate.get("min_row_count", 3)):
        failures.append(f"{tag}:insufficient_row_count:{row_count}")
    if avg_score > float(gate.get("max_avg_composite_signal_score", 0.8)):
        failures.append(f"{tag}:avg_score_too_high:{avg_score:.6f}")
    if reduce_ratio > float(gate.get("max_reduce_candidate_ratio", 0.4)):
        failures.append(f"{tag}:reduce_ratio_too_high:{reduce_ratio:.6f}")
    if watch_ratio > float(gate.get("max_watch_candidate_ratio", 0.8)):
        failures.append(f"{tag}:watch_ratio_too_high:{watch_ratio:.6f}")
    if gate.get("require_observation_only_guard_active", True) and not guard_active:
        failures.append(f"{tag}:observation_only_guard_inactive")
    return failures


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
    default_eval = root / "docs" / "final" / "artifacts" / "chronicle_history_news_signal_weekly_eval_latest.json"
    default_thresholds = root / "docs" / "final" / "artifacts" / "chronicle_history_news_weekly_alert_thresholds_v1.json"
    default_report = root / "docs" / "final" / "artifacts" / "chronicle_history_news_weekly_alert_latest.json"

    ap = argparse.ArgumentParser(description="Check chronicle-history-news weekly alert conditions.")
    ap.add_argument("--weekly-eval-json", default=str(default_eval))
    ap.add_argument("--thresholds-json", default=str(default_thresholds))
    ap.add_argument("--report-json", default=str(default_report))
    ap.add_argument("--webhook-env", default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--strict-on", choices=["critical", "any"], default="critical")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    weekly_eval = _load_json(Path(args.weekly_eval_json))
    thresholds = _load_json(Path(args.thresholds_json))

    row_count = int(weekly_eval.get("row_count", 0) or 0)
    avg_score = float(weekly_eval.get("avg_composite_signal_score", 0.0) or 0.0)
    candidate_counts = weekly_eval.get("candidate_decision_counts", {})
    hold_count = int(candidate_counts.get("HOLD", 0) or 0)
    watch_count = int(candidate_counts.get("WATCH", 0) or 0)
    reduce_count = int(candidate_counts.get("REDUCE", 0) or 0)
    total = max(1, hold_count + watch_count + reduce_count)
    watch_ratio = watch_count / total
    reduce_ratio = reduce_count / total
    guard_active = bool(weekly_eval.get("observation_only_guard_active", False))

    warning_gate = thresholds.get("warning") if isinstance(thresholds.get("warning"), dict) else thresholds
    critical_gate = thresholds.get("critical") if isinstance(thresholds.get("critical"), dict) else thresholds

    warning_failures = _eval_gate(
        row_count=row_count,
        avg_score=avg_score,
        watch_ratio=watch_ratio,
        reduce_ratio=reduce_ratio,
        guard_active=guard_active,
        gate=warning_gate,
        tag="warning",
    )
    critical_failures = _eval_gate(
        row_count=row_count,
        avg_score=avg_score,
        watch_ratio=watch_ratio,
        reduce_ratio=reduce_ratio,
        guard_active=guard_active,
        gate=critical_gate,
        tag="critical",
    )
    failures = warning_failures + critical_failures
    severity = "CRITICAL" if critical_failures else ("WARNING" if warning_failures else "OK")
    ok = len(failures) == 0

    report = {
        "schema": "chronicle_history_news_weekly_alert_v1",
        "checked_at_utc": _to_iso(now),
        "weekly_eval_path": str(Path(args.weekly_eval_json)),
        "thresholds_path": str(Path(args.thresholds_json)),
        "row_count": row_count,
        "avg_composite_signal_score": round(avg_score, 6),
        "watch_candidate_ratio": round(watch_ratio, 6),
        "reduce_candidate_ratio": round(reduce_ratio, 6),
        "observation_only_guard_active": guard_active,
        "severity": severity,
        "warning_failures": warning_failures,
        "critical_failures": critical_failures,
        "failures": failures,
        "ok": ok
    }

    webhook = str(os.environ.get(args.webhook_env, "")).strip()
    dispatch: dict[str, Any]
    if failures and webhook:
        payload = {
            "source": "chronicle_history_news_weekly_alert_v1",
            "checked_at_utc": report["checked_at_utc"],
            "row_count": row_count,
            "avg_composite_signal_score": round(avg_score, 6),
            "watch_candidate_ratio": round(watch_ratio, 6),
            "reduce_candidate_ratio": round(reduce_ratio, 6),
            "observation_only_guard_active": guard_active,
            "failures": failures,
            "warning_failures": warning_failures,
            "critical_failures": critical_failures,
            "severity": severity,
            "track": "B",
            "governance_state": "S1_SHADOW",
            "observation_mode": "KEEP_OBSERVATION_ONLY",
        }
        dispatch = _dispatch_webhook(webhook, payload)
    elif failures and not webhook:
        dispatch = {"status": "skipped", "reason": "webhook_not_configured"}
    else:
        dispatch = {"status": "skipped", "reason": "no_failures"}
    report["dispatch"] = dispatch

    Path(args.report_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    strict_should_fail = bool(critical_failures) if args.strict_on == "critical" else bool(failures)
    if args.strict and strict_should_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
