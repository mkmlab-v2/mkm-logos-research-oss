#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit governance alert from policy audit summary.")
    ap.add_argument(
        "--audit-summary-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json",
    )
    ap.add_argument(
        "--out-alert-json",
        default="docs/final/artifacts/pre_news_shadow_policy_governance_alert_latest.json",
    )
    ap.add_argument(
        "--append-alert-log-jsonl",
        default="reports/pre_news_shadow_policy_governance_alert_log.jsonl",
    )
    ap.add_argument("--change-count-threshold", type=int, default=2)
    args = ap.parse_args()

    summary_path = resolve(args.audit_summary_json)
    out_path = resolve(args.out_alert_json)
    log_path = resolve(args.append_alert_log_jsonl)
    threshold = max(1, int(args.change_count_threshold))

    summary = load_json(summary_path)
    metrics = summary.get("metrics") if isinstance(summary.get("metrics"), dict) else {}
    state = summary.get("current_policy_state") if isinstance(summary.get("current_policy_state"), dict) else {}

    change_count = int(metrics.get("change_count_window", 0) or 0)
    has_two_person_approval = bool(state.get("approved_by_1")) and bool(state.get("approved_by_2"))
    required_meta = (
        bool(state.get("policy_version")),
        bool(state.get("approved_by")),
        bool(state.get("effective_from_utc")),
        bool(state.get("policy_fingerprint_sha256")),
        has_two_person_approval,
    )
    has_meta_gap = not all(required_meta)
    has_alert = bool(change_count > threshold or has_meta_gap)
    reasons: list[str] = []
    if change_count > threshold:
        reasons.append(f"change_count_window={change_count} > threshold={threshold}")
    if has_meta_gap:
        reasons.append("policy governance metadata incomplete")
    if not has_two_person_approval:
        reasons.append("two-person approval missing")

    webhook = os.getenv("MKM_PRE_NEWS_POLICY_GOVERNANCE_ALERT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or ""
    notified = False
    notify_status = "skipped_no_alert"
    if has_alert:
        if webhook:
            payload = {
                "event": "pre_news_shadow_policy_governance_alert_v1",
                "generated_at_utc": now(),
                "severity": "warning",
                "reasons": reasons,
                "change_count_window": change_count,
                "threshold": threshold,
                "audit_summary_json": str(summary_path),
            }
            ok, status = post_webhook(webhook, payload)
            notified = ok
            notify_status = status if ok else f"failed:{status}"
        else:
            notify_status = "skipped_no_webhook"

    out = {
        "schema": "pre_news_shadow_policy_governance_alert_v1",
        "generated_at_utc": now(),
        "audit_summary_json": str(summary_path),
        "has_alert": has_alert,
        "severity": "warning" if has_alert else "none",
        "change_count_window": change_count,
        "change_count_threshold": threshold,
        "has_policy_metadata_gap": has_meta_gap,
        "has_two_person_approval": has_two_person_approval,
        "reasons": reasons,
        "notified": notified,
        "notify_status": notify_status,
    }
    write_json(out_path, out)
    if has_alert:
        append_jsonl(log_path, out)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

