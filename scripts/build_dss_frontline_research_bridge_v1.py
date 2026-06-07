#!/usr/bin/env python3
"""Bridge report: DSS frontline runnable commands vs workspace script availability."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DSS_ROOT = ROOT / "projects/dss-4d-ingest"
DEFAULT_FRONTLINE = DSS_ROOT / "outputs/frontline_latest_status.json"
DEFAULT_OUT = ROOT / "reports/dss_frontline_research_bridge_latest.json"

PRIORITY_RUN_KEYS = (
    "dss",
    "apocrypha",
    "fusion_join_gate",
    "authority_readiness",
    "apocrypha_hebrew_priority_plan",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _script_exists_in_command(command: str) -> bool:
    parts = command.split()
    for part in parts:
        if part.endswith(".py") and not part.startswith("-"):
            candidate = DSS_ROOT / part.replace("outputs/", "outputs/").split("/")[-1]
            # command uses bare script name in cwd
            if (DSS_ROOT / Path(part).name).is_file():
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frontline-status-json", type=Path, default=DEFAULT_FRONTLINE)
    ap.add_argument("--dss-project-root", type=Path, default=DSS_ROOT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py_files = list(args.dss_project_root.glob("*.py")) if args.dss_project_root.is_dir() else []
    cycle_tag = None
    cycle_report: Path | None = None
    runs: dict[str, Any] = {}
    if args.frontline_status_json.is_file():
        front = _load(args.frontline_status_json)
        cycle_tag = front.get("latest_cycle_tag")
        rel = str(front.get("latest_cycle_report") or "").replace("\\", "/")
        if rel:
            cycle_report = args.dss_project_root / rel
            if cycle_report.is_file():
                runs = _load(cycle_report).get("runs") or {}

    priority_commands: list[dict[str, Any]] = []
    for key in PRIORITY_RUN_KEYS:
        step = runs.get(key) if isinstance(runs.get(key), dict) else {}
        cmd = str(step.get("command") or "")
        priority_commands.append(
            {
                "run_key": key,
                "status": step.get("status"),
                "exit_code": step.get("exit_code"),
                "command": cmd,
                "cwd": step.get("cwd"),
                "script_present_in_dss_root": _script_exists_in_command(cmd) if cmd else False,
            }
        )

    scripts_present = len(py_files)
    runnable_locally = scripts_present > 0
    recommendation = (
        "run_frontline_in_dss_project_root"
        if runnable_locally
        else "watch_missing_dss_ingest_scripts_use_smoke_bootstrap"
    )

    payload = {
        "schema": "dss_frontline_research_bridge_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "dss_project_root": str(args.dss_project_root),
        "python_scripts_in_root_count": scripts_present,
        "latest_cycle_tag": cycle_tag,
        "latest_cycle_report": str(cycle_report) if cycle_report else None,
        "priority_run_commands": priority_commands,
        "recommendation": recommendation,
        "workspace_followup_after_frontline": [
            "py scripts/build_dss_authority_readiness_reconciliation_v1.py",
            "py scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py --merge-into docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl",
            "py scripts/build_biblical_resonance_research_production_ab_v1.py",
            "py scripts/build_dss_ndjson_resonance_uplift_report_v1.py",
        ],
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "recommendation": recommendation}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
