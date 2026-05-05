#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_task_profile_guard_latest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_query(task_name: str) -> tuple[int, str]:
    cp = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "LIST"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return cp.returncode, (cp.stdout or "") + (cp.stderr or "")


def _extract_value(text: str, key: str) -> str:
    prefix = f"{key}:"
    for line in text.splitlines():
        if line.strip().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard scheduled task command includes holdout profile.")
    ap.add_argument("--task-name", default="\\GeneralProphecyDailyQueueV1")
    ap.add_argument("--required-profile", choices=("research", "ops"), default="ops")
    ap.add_argument("--required-include-logos-v2", choices=("true", "false"), default="true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-exit", action="store_true", help="Exit 2 when profile mismatch")
    args = ap.parse_args()

    code, raw = _run_query(args.task_name)
    if code != 0:
        out = {
            "schema": "general_prophecy_task_profile_guard_v1",
            "generated_at_utc": utc_now(),
            "task_name": args.task_name,
            "query_ok": False,
            "all_pass": False,
            "decision": "TASK_QUERY_FAILED",
            "details": {"error": raw.strip()},
        }
        out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "decision": out["decision"]}, ensure_ascii=False))
        return 2 if args.strict_exit else 0

    task_to_run = _extract_value(raw, "Task To Run")
    expected_token = f"-HoldoutGateProfile {args.required_profile}"
    expected_logos_token = f"-IncludeLogosV2 {args.required_include_logos_v2}"
    has_profile = expected_token in task_to_run
    has_logos_toggle = expected_logos_token in task_to_run
    all_pass = has_profile and has_logos_toggle

    out: dict[str, Any] = {
        "schema": "general_prophecy_task_profile_guard_v1",
        "generated_at_utc": utc_now(),
        "task_name": args.task_name,
        "query_ok": True,
        "all_pass": all_pass,
        "decision": "TASK_PROFILE_AND_LOGOS_OK" if all_pass else "TASK_PROFILE_OR_LOGOS_MISMATCH",
        "details": {
            "required_profile": args.required_profile,
            "expected_token": expected_token,
            "required_include_logos_v2": args.required_include_logos_v2,
            "expected_include_logos_token": expected_logos_token,
            "has_profile_token": has_profile,
            "has_include_logos_token": has_logos_toggle,
            "task_to_run": task_to_run,
        },
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": out["decision"], "all_pass": all_pass}, ensure_ascii=False))
    if args.strict_exit and not all_pass:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
