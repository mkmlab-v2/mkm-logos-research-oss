#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def read_last_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows[-max(0, limit) :] if limit > 0 else rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly pre-news audit bundle.")
    ap.add_argument("--weekly-report-json", default="docs/final/artifacts/pre_news_shadow_weekly_report_latest.json")
    ap.add_argument(
        "--policy-audit-summary-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json",
    )
    ap.add_argument(
        "--policy-governance-alert-json",
        default="docs/final/artifacts/pre_news_shadow_policy_governance_alert_latest.json",
    )
    ap.add_argument(
        "--policy-state-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_state_latest.json",
    )
    ap.add_argument(
        "--policy-change-log-jsonl",
        default="reports/pre_news_shadow_stage_threshold_policy_change_log.jsonl",
    )
    ap.add_argument(
        "--holdout-replay-json",
        default="docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json",
    )
    ap.add_argument(
        "--holdout-lock-json",
        default="docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json",
    )
    ap.add_argument("--tail-policy-change-rows", type=int, default=20)
    ap.add_argument(
        "--out-json",
        default="docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_latest.json",
    )
    ap.add_argument(
        "--out-dated-json",
        default="docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_{date}.json",
        help="Dated archive output path template. Use {date} placeholder for UTC date.",
    )
    ap.add_argument(
        "--hash-manifest-json",
        default="docs/final/artifacts/pre_news_shadow_weekly_audit_bundle_hash_manifest_latest.json",
    )
    args = ap.parse_args()

    weekly = read_json(resolve(args.weekly_report_json))
    policy_summary = read_json(resolve(args.policy_audit_summary_json))
    policy_alert = read_json(resolve(args.policy_governance_alert_json))
    policy_state = read_json(resolve(args.policy_state_json))
    holdout = read_json(resolve(args.holdout_replay_json))
    holdout_lock = read_json(resolve(args.holdout_lock_json))
    policy_changes_tail = read_last_jsonl(resolve(args.policy_change_log_jsonl), int(args.tail_policy_change_rows))

    bundle = {
        "schema": "pre_news_shadow_weekly_audit_bundle_v1",
        "generated_at_utc": now(),
        "inputs": {
            "weekly_report_json": str(resolve(args.weekly_report_json)),
            "policy_audit_summary_json": str(resolve(args.policy_audit_summary_json)),
            "policy_governance_alert_json": str(resolve(args.policy_governance_alert_json)),
            "policy_state_json": str(resolve(args.policy_state_json)),
            "policy_change_log_jsonl": str(resolve(args.policy_change_log_jsonl)),
            "holdout_replay_json": str(resolve(args.holdout_replay_json)),
            "holdout_lock_json": str(resolve(args.holdout_lock_json)),
        },
        "weekly_report": {
            "generated_at_utc": weekly.get("generated_at_utc"),
            "risk_summary": weekly.get("risk_summary"),
            "metrics": weekly.get("metrics"),
            "promotion_gate": weekly.get("promotion_gate"),
        },
        "policy_audit_summary": {
            "generated_at_utc": policy_summary.get("generated_at_utc"),
            "metrics": policy_summary.get("metrics"),
            "risk_summary": policy_summary.get("risk_summary"),
        },
        "policy_governance_alert": policy_alert,
        "policy_state": policy_state,
        "policy_change_log_tail": policy_changes_tail,
        "holdout_replay_summary": holdout.get("summary"),
        "holdout_lock_manifest": holdout_lock,
    }

    out = resolve(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    dated = None
    dated_template = str(args.out_dated_json or "").strip()
    if dated_template:
        dated_path_raw = dated_template.format(date=today_utc())
        dated = resolve(dated_path_raw)
        dated.parent.mkdir(parents=True, exist_ok=True)
        dated.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(dated))

    manifest = {
        "schema": "pre_news_shadow_weekly_audit_bundle_hash_manifest_v1",
        "generated_at_utc": now(),
        "latest_bundle_path": str(out),
        "latest_bundle_sha256": sha256_file(out),
        "dated_bundle_path": str(dated) if dated is not None else None,
        "dated_bundle_sha256": sha256_file(dated) if dated is not None else None,
    }
    manifest_path = resolve(args.hash_manifest_json)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(manifest_path))
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

