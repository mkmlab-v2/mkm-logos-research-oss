#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
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


def run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def mismatch_sha(sha: str) -> str:
    if not sha:
        return "0" * 64
    first = "0" if sha[0] != "0" else "1"
    return first + sha[1:]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run holdout lock mismatch drill for pre-news weekly gate.")
    ap.add_argument(
        "--lock-manifest-json",
        default="docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_v1.json",
    )
    ap.add_argument(
        "--mismatch-lock-manifest-json",
        default="docs/final/artifacts/global_atom_news_holdout_dataset_lock_manifest_mismatch_drill_latest.json",
    )
    ap.add_argument("--log-jsonl", default="reports/pre_news_shadow_projection_log.jsonl")
    ap.add_argument("--alert-log-jsonl", default="reports/pre_news_shadow_task_health_alert_log.jsonl")
    ap.add_argument(
        "--holdout-replay-json",
        default="docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json",
    )
    ap.add_argument(
        "--policy-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_v1.json",
    )
    ap.add_argument(
        "--weekly-out-json",
        default="docs/final/artifacts/pre_news_shadow_weekly_report_lock_mismatch_drill_latest.json",
    )
    ap.add_argument(
        "--drill-report-json",
        default="docs/final/artifacts/pre_news_shadow_holdout_lock_mismatch_drill_latest.json",
    )
    args = ap.parse_args()

    lock_src = resolve(args.lock_manifest_json)
    lock_dst = resolve(args.mismatch_lock_manifest_json)
    weekly_out = resolve(args.weekly_out_json)
    drill_out = resolve(args.drill_report_json)

    src = read_json(lock_src)
    bad = dict(src)
    bad["generated_at_utc"] = now()
    bad["dataset_sha256"] = mismatch_sha(str(src.get("dataset_sha256", "") or ""))
    bad["note"] = "Intentional mismatch for lock drill."
    write_json(lock_dst, bad)

    cmd = [
        sys.executable,
        "scripts/build_global_atom_pre_news_shadow_weekly_report_v1.py",
        "--log-jsonl",
        str(resolve(args.log_jsonl)),
        "--alert-log-jsonl",
        str(resolve(args.alert_log_jsonl)),
        "--holdout-replay-json",
        str(resolve(args.holdout_replay_json)),
        "--holdout-dataset-lock-json",
        str(lock_dst),
        "--enforce-holdout-dataset-lock",
        "--stage-threshold-policy-json",
        str(resolve(args.policy_json)),
        "--enforce-policy-effective-from",
        "--window-days",
        "7",
        "--out-json",
        str(weekly_out),
    ]
    result = run(cmd)
    weekly = read_json(weekly_out)
    gate = weekly.get("promotion_gate") if isinstance(weekly.get("promotion_gate"), dict) else {}
    rejected = weekly.get("rejected_stage_counts") if isinstance(weekly.get("rejected_stage_counts"), list) else []
    has_hash_reject = any(isinstance(r, dict) and r.get("reject_reason") == "holdout_dataset_hash_mismatch" for r in rejected)
    ok = (
        result["exit_code"] == 0
        and gate.get("enabled") is False
        and gate.get("holdout_dataset_lock_ok") is False
        and has_hash_reject
    )

    report = {
        "schema": "pre_news_shadow_holdout_lock_mismatch_drill_v1",
        "generated_at_utc": now(),
        "lock_manifest_src_json": str(lock_src),
        "lock_manifest_mismatch_json": str(lock_dst),
        "weekly_report_json": str(weekly_out),
        "command_result": result,
        "gate_snapshot": {
            "enabled": gate.get("enabled"),
            "holdout_dataset_lock_ok": gate.get("holdout_dataset_lock_ok"),
            "expected_sha": gate.get("holdout_dataset_expected_sha256"),
            "actual_sha": gate.get("holdout_dataset_actual_sha256"),
            "hash_mismatch_reject_present": has_hash_reject,
        },
        "ok": ok,
    }
    write_json(drill_out, report)
    print(json.dumps({"ok": ok, "report": str(drill_out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

