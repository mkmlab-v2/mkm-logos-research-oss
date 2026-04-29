#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows[-limit:]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build single-file ops dashboard for pre-news shadow chain.")
    ap.add_argument(
        "--weekly-report-json",
        default=str(ART / "pre_news_shadow_weekly_report_latest.json"),
    )
    ap.add_argument(
        "--policy-governance-alert-json",
        default=str(ART / "pre_news_shadow_policy_governance_alert_latest.json"),
    )
    ap.add_argument(
        "--task-health-alert-json",
        default=str(ART / "pre_news_shadow_task_health_alert_latest.json"),
    )
    ap.add_argument(
        "--weekly-audit-bundle-json",
        default=str(ART / "pre_news_shadow_weekly_audit_bundle_latest.json"),
    )
    ap.add_argument(
        "--weekly-audit-hash-manifest-json",
        default=str(ART / "pre_news_shadow_weekly_audit_bundle_hash_manifest_latest.json"),
    )
    ap.add_argument(
        "--holdout-lock-drill-json",
        default=str(ART / "pre_news_shadow_holdout_lock_mismatch_drill_latest.json"),
    )
    ap.add_argument(
        "--policy-governance-drill-json",
        default=str(ART / "pre_news_shadow_policy_governance_drill_latest.json"),
    )
    ap.add_argument(
        "--health-alert-drill-json",
        default=str(ART / "pre_news_shadow_alert_drill_latest.json"),
    )
    ap.add_argument(
        "--policy-alert-log-jsonl",
        default="reports/pre_news_shadow_policy_governance_alert_log.jsonl",
    )
    ap.add_argument(
        "--task-health-alert-log-jsonl",
        default="reports/pre_news_shadow_task_health_alert_log.jsonl",
    )
    ap.add_argument(
        "--projection-log-jsonl",
        default="reports/pre_news_shadow_projection_log.jsonl",
    )
    ap.add_argument("--tail-rows", type=int, default=5)
    ap.add_argument(
        "--out-json",
        default=str(ART / "pre_news_shadow_ops_status_latest.json"),
    )
    args = ap.parse_args()

    weekly = read_json(resolve(args.weekly_report_json))
    policy_alert = read_json(resolve(args.policy_governance_alert_json))
    health_alert = read_json(resolve(args.task_health_alert_json))
    bundle = read_json(resolve(args.weekly_audit_bundle_json))
    bundle_hash_manifest = read_json(resolve(args.weekly_audit_hash_manifest_json))
    drill_lock = read_json(resolve(args.holdout_lock_drill_json))
    drill_policy = read_json(resolve(args.policy_governance_drill_json))
    drill_health = read_json(resolve(args.health_alert_drill_json))

    policy_alert_tail = read_jsonl_tail(resolve(args.policy_alert_log_jsonl), args.tail_rows)
    task_alert_tail = read_jsonl_tail(resolve(args.task_health_alert_log_jsonl), args.tail_rows)
    projection_tail = read_jsonl_tail(resolve(args.projection_log_jsonl), args.tail_rows)

    promotion_gate = weekly.get("promotion_gate", {}) if isinstance(weekly.get("promotion_gate"), dict) else {}
    metrics = weekly.get("metrics", {}) if isinstance(weekly.get("metrics"), dict) else {}

    drill_items = [
        {"name": "holdout_lock_mismatch", "ok": drill_lock.get("ok"), "generated_at_utc": drill_lock.get("generated_at_utc")},
        {"name": "policy_governance", "ok": drill_policy.get("ok"), "generated_at_utc": drill_policy.get("generated_at_utc")},
        {"name": "task_health_alert", "ok": drill_health.get("ok"), "generated_at_utc": drill_health.get("generated_at_utc")},
    ]
    known = [d for d in drill_items if isinstance(d.get("ok"), bool)]
    failed = [d for d in known if d.get("ok") is False]

    out_doc = {
        "schema": "pre_news_shadow_ops_status_v1",
        "generated_at_utc": now(),
        "summary": {
            "promotion_gate_enabled": bool(promotion_gate.get("enabled", False)),
            "holdout_dataset_lock_ok": promotion_gate.get("holdout_dataset_lock_ok"),
            "policy_governance_has_alert": bool(policy_alert.get("has_alert", False)),
            "task_health_has_alert": bool(health_alert.get("has_alert", False)),
            "weekly_sample_count": metrics.get("sample_count_7d"),
            "recent_projection_rows": len(projection_tail),
            "drill_status": "fail" if failed else ("ok" if known else "unknown"),
            "drill_failed_count": len(failed),
        },
        "gate_status": {
            "promotion_gate": promotion_gate,
            "weekly_metrics": metrics,
            "risk_summary": weekly.get("risk_summary"),
        },
        "latest_alerts": {
            "policy_governance_alert": policy_alert,
            "task_health_alert": health_alert,
        },
        "recent_alert_log_tail": {
            "policy_governance": policy_alert_tail,
            "task_health": task_alert_tail,
        },
        "recent_projection_log_tail": projection_tail,
        "recent_drills": drill_items,
        "recent_bundle_paths": {
            "weekly_audit_bundle_json": str(resolve(args.weekly_audit_bundle_json)),
            "weekly_audit_bundle_hash_manifest_json": str(resolve(args.weekly_audit_hash_manifest_json)),
            "latest_bundle_path": bundle_hash_manifest.get("latest_bundle_path"),
            "dated_bundle_path": bundle_hash_manifest.get("dated_bundle_path"),
            "weekly_audit_bundle_generated_at_utc": bundle.get("generated_at_utc"),
        },
        "sources": {
            "weekly_report_json": str(resolve(args.weekly_report_json)),
            "policy_governance_alert_json": str(resolve(args.policy_governance_alert_json)),
            "task_health_alert_json": str(resolve(args.task_health_alert_json)),
            "holdout_lock_drill_json": str(resolve(args.holdout_lock_drill_json)),
            "policy_governance_drill_json": str(resolve(args.policy_governance_drill_json)),
            "health_alert_drill_json": str(resolve(args.health_alert_drill_json)),
            "policy_alert_log_jsonl": str(resolve(args.policy_alert_log_jsonl)),
            "task_health_alert_log_jsonl": str(resolve(args.task_health_alert_log_jsonl)),
            "projection_log_jsonl": str(resolve(args.projection_log_jsonl)),
        },
    }

    out_path = resolve(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
