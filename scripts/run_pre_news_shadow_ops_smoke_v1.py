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


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run pre-news shadow ops smoke checks in one command.")
    ap.add_argument(
        "--ops-status-json",
        default="docs/final/artifacts/pre_news_shadow_ops_status_latest.json",
    )
    ap.add_argument(
        "--drill-summary-json",
        default="docs/final/artifacts/pre_news_shadow_monthly_drill_summary_alert_latest.json",
    )
    ap.add_argument(
        "--workflow-checklist-json",
        default="docs/final/artifacts/pre_news_shadow_policy_change_approval_workflow_v1.json",
    )
    ap.add_argument(
        "--out-json",
        default="docs/final/artifacts/pre_news_shadow_ops_smoke_latest.json",
    )
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(
        run_step(
            "build_ops_status_dashboard",
            [sys.executable, "scripts/build_pre_news_shadow_ops_status_dashboard_v1.py"],
        )
    )
    steps.append(
        run_step(
            "build_monthly_drill_summary_alert",
            [sys.executable, "scripts/alert_pre_news_shadow_monthly_drill_summary_v1.py"],
        )
    )
    workflow_path = resolve(args.workflow_checklist_json)
    checklist_ok = workflow_path.is_file()
    steps.append(
        {
            "name": "policy_change_workflow_checklist_exists",
            "cmd": ["exists", str(workflow_path)],
            "exit_code": 0 if checklist_ok else 1,
            "ok": checklist_ok,
            "stdout": str(workflow_path),
            "stderr": "" if checklist_ok else "missing workflow checklist json",
        }
    )

    ops_status = read_json(resolve(args.ops_status_json))
    drill_summary = read_json(resolve(args.drill_summary_json))

    all_ok = all(bool(s.get("ok", False)) for s in steps)
    smoke = {
        "schema": "pre_news_shadow_ops_smoke_v1",
        "generated_at_utc": now(),
        "all_ok": all_ok,
        "steps": steps,
        "snapshot": {
            "ops_status_summary": ops_status.get("summary"),
            "monthly_drill_summary_line": drill_summary.get("summary_line"),
            "monthly_drill_all_ok": drill_summary.get("all_ok"),
        },
    }
    out_path = resolve(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(out_path)}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
