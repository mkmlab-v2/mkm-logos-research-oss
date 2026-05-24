#!/usr/bin/env python3
"""Push all ops pack files via stdio MCP using pre-emitted args JSON files."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RUNNER = ROOT / "scripts" / "nl_mcp_run_add_source_from_args_file_v1.py"
SKIP = {"00_ops_command_handoff_snippet.md", "parallel_ops_run_2026-05-23_latest.json"}


def main() -> int:
    index = json.loads((ROOT / "reports/notebooklm_ops_command_sync_pack_v1/index.json").read_text(encoding="utf-8"))
    rows = []
    for name in index["files"]:
        if name in SKIP:
            continue
        safe = name.replace("/", "_")
        args_path = REPORTS / f"tmp_nl_{safe}.json"
        if not args_path.is_file():
            print(json.dumps({"title": name, "success": False, "error": "no args file"}))
            rows.append(False)
            continue
        r = subprocess.run([sys.executable, str(RUNNER), str(args_path)], capture_output=True, text=True)
        line = (r.stdout or r.stderr).strip().splitlines()[-1] if r.stdout or r.stderr else ""
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            row = {"title": name, "success": False, "error": line or r.stderr}
        rows.append(row.get("success"))
        print(json.dumps(row, ensure_ascii=False))
    return 0 if all(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
