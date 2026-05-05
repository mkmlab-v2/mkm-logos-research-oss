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


def read_json(path: Path) -> dict[str, Any]:
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


def build_item(name: str, path: Path, rc: int | None) -> dict[str, Any]:
    obj = read_json(path)
    ok_by_json = obj.get("ok") if isinstance(obj.get("ok"), bool) else None
    ok_by_rc = (rc == 0) if rc is not None else None
    if ok_by_json is not None:
        ok = ok_by_json
    elif ok_by_rc is not None:
        ok = ok_by_rc
    else:
        ok = False
    return {
        "name": name,
        "report_json": str(path),
        "ok": bool(ok),
        "generated_at_utc": obj.get("generated_at_utc"),
        "exit_code": rc,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Send one-line monthly pre-news drill summary alert.")
    ap.add_argument(
        "--holdout-lock-drill-json",
        default="docs/final/artifacts/pre_news_shadow_holdout_lock_mismatch_drill_latest.json",
    )
    ap.add_argument(
        "--policy-governance-drill-json",
        default="docs/final/artifacts/pre_news_shadow_policy_governance_drill_latest.json",
    )
    ap.add_argument("--holdout-lock-exit-code", type=int, default=None)
    ap.add_argument("--policy-governance-exit-code", type=int, default=None)
    ap.add_argument(
        "--out-alert-json",
        default="docs/final/artifacts/pre_news_shadow_monthly_drill_summary_alert_latest.json",
    )
    ap.add_argument(
        "--append-log-jsonl",
        default="reports/pre_news_shadow_monthly_drill_summary_alert_log.jsonl",
    )
    args = ap.parse_args()

    lock_path = resolve(args.holdout_lock_drill_json)
    policy_path = resolve(args.policy_governance_drill_json)
    out_path = resolve(args.out_alert_json)
    log_path = resolve(args.append_log_jsonl)

    checks = [
        build_item("holdout_lock_mismatch", lock_path, args.holdout_lock_exit_code),
        build_item("policy_governance", policy_path, args.policy_governance_exit_code),
    ]
    failed = [c["name"] for c in checks if not c["ok"]]
    all_ok = len(failed) == 0
    summary_line = (
        "Pre-News monthly drills: PASS (2/2)."
        if all_ok
        else f"Pre-News monthly drills: FAIL ({2 - len(failed)}/2), failed={','.join(failed)}."
    )

    webhook = os.getenv("MKM_PRE_NEWS_SHADOW_ALERT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or ""
    notified = False
    notify_status = "skipped_no_webhook"
    if webhook:
        payload = {
            "event": "pre_news_shadow_monthly_drill_summary_alert_v1",
            "generated_at_utc": now(),
            "severity": "info" if all_ok else "warning",
            "summary_line": summary_line,
            "failed_checks": failed,
            "checks": checks,
        }
        ok, status = post_webhook(webhook, payload)
        notified = ok
        notify_status = status if ok else f"failed:{status}"

    alert = {
        "schema": "pre_news_shadow_monthly_drill_summary_alert_v1",
        "generated_at_utc": now(),
        "has_alert": not all_ok,
        "severity": "none" if all_ok else "warning",
        "all_ok": all_ok,
        "summary_line": summary_line,
        "checks": checks,
        "failed_checks": failed,
        "notified": notified,
        "notify_status": notify_status,
    }
    write_json(out_path, alert)
    append_jsonl(log_path, alert)
    print(str(out_path))
    print(summary_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
