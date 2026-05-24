#!/usr/bin/env python3
"""Apply MISSION_LOG + CENTRAL-aligned NotebookLM optimal setup (local SSOT + packs).

Does NOT delete Google notebooks (use web UI with delete_guard JSON).
Writes: reports/notebooklm_optimal_setup_latest.json

Usage:
  py scripts/apply_notebooklm_optimal_setup_v1.py
  py scripts/apply_notebooklm_optimal_setup_v1.py --push-ops-url https://notebooklm.google.com/notebook/<uuid>
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP_SSOT = ROOT / "docs/final/artifacts/notebooklm_optimal_setup_v1.json"
MIGRATION = ROOT / "reports/notebooklm_archive_migration_plan_v1_latest.json"
MISSION = ROOT / "MISSION_LOG.md"
OUT = ROOT / "reports/notebooklm_optimal_setup_latest.json"


def _run_build(script: str) -> dict:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    line = (r.stdout or r.stderr or "").strip().splitlines()[-1] if r.stdout or r.stderr else ""
    try:
        payload = json.loads(line) if line.startswith("{") else {"raw": line, "exit": r.returncode}
    except json.JSONDecodeError:
        payload = {"raw": line, "exit": r.returncode}
    payload["exit_code"] = r.returncode
    return payload


def _mission_log_next_actions(text: str) -> list[str]:
    rows: list[str] = []
    in_table = False
    for line in text.splitlines():
        if "| 레인 | 다음 1타 |" in line:
            in_table = True
            continue
        if in_table:
            if line.startswith("| **") and "|" in line[1:]:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2 and parts[0] != "레인":
                    lane, action = parts[0], parts[1]
                    if "MS" in lane and "배제" in action:
                        continue
                    rows.append(f"{lane}: {action}")
            if line.startswith("### ") and "다음 1타" not in line:
                break
    return rows[:12]


def _pack_file_count(pack_dir: Path) -> int:
    if not pack_dir.is_dir():
        return 0
    return len([p for p in pack_dir.iterdir() if p.is_file() and p.name != "index.json"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push-ops-url", help="NotebookLM URL for 00_OPS after web create")
    args = ap.parse_args()

    setup = json.loads(SETUP_SSOT.read_text(encoding="utf-8"))
    mission_text = MISSION.read_text(encoding="utf-8", errors="replace") if MISSION.is_file() else ""

    ops_build = _run_build("build_notebooklm_ops_command_sync_pack_v1.py")
    farm_build = _run_build("build_notebooklm_smartfarm_geumsan_sync_pack_v1.py")

    ops_pack = ROOT / setup["roles"]["ops_command"]["pack"]
    farm_pack = ROOT / setup["roles"]["smartfarm_domain"]["pack"]

    report = {
        "schema": "notebooklm_optimal_setup_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ssot": str(SETUP_SSOT.relative_to(ROOT)).replace("\\", "/"),
        "target_home": [
            setup["roles"]["ops_command"]["name"],
            setup["roles"]["smartfarm_domain"]["name"],
            setup["roles"]["archive_hub"]["name"],
        ],
        "mission_log_next_actions": _mission_log_next_actions(mission_text),
        "packs": {
            "ops": {"dir": str(ops_pack.relative_to(ROOT)), "files": _pack_file_count(ops_pack), "build": ops_build},
            "smartfarm": {"dir": str(farm_pack.relative_to(ROOT)), "files": _pack_file_count(farm_pack), "build": farm_build},
        },
        "delete_guard": setup["delete_guard"],
        "web_steps_remaining": [
            "Create 00_OPS_지휘부_2026Q2 notebook in NL web",
            f"Upload all files from {ops_pack.relative_to(ROOT)}/",
            "Delete [ARCHIVED] 03 and 04 from home (optional: export to 99 first)",
            "Copy 99_ARCHIVE card link → MCP add_notebook + fix library.json stale P2 UUID",
            "MCP select_notebook: 00-ops-command-2026q2 for daily ops queries",
        ],
        "push_ops_url": args.push_ops_url,
    }

    if args.push_ops_url:
        report["push_ops_note"] = (
            "Run MCP add_source type=text for each pack file with notebook_url=push_ops_url "
            "(agent or scripts/push_notebooklm_ops_command_pack_mcp_v1.py when available)"
        )

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "target_home": report["target_home"], "ops_files": report["packs"]["ops"]["files"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
