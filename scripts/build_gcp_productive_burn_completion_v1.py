#!/usr/bin/env python3
"""Summarize productive burn delegation status (local + optional cloud pull)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "gcp_productive_burn_completion_v1_latest.json"
SANDBOX = ROOT / "reports" / "sandbox"
DELEGATION = ROOT / "reports" / "delegation_gcp_credit_productive_burn_approval_map_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cloud-log-dir", type=Path, default=None, help="Pulled ~/productive_burn_logs")
    args = ap.parse_args()

    lane_summaries: list[dict] = []
    for pattern in ("*_summary.json", "*_P3*.json"):
        for path in sorted(SANDBOX.glob(pattern)):
            if path.name.startswith("gcp_productive"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("schema") == "gcp_productive_burn_lane_v1":
                lane_summaries.append(data)

    jsonl_files = list(SANDBOX.glob("gcp_burn_*.jsonl")) + list(SANDBOX.glob("btrack_fills_vertex*.jsonl"))
    jsonl_rows = 0
    for p in jsonl_files:
        try:
            jsonl_rows += sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())
        except OSError:
            pass

    delegation = {}
    if DELEGATION.is_file():
        delegation = json.loads(DELEGATION.read_text(encoding="utf-8"))

    payload = {
        "schema": "gcp_productive_burn_completion_v1",
        "generated_at_utc": _utc(),
        "delegation_approval": "user_full_autonomy_to_completion_2026-06-09",
        "mode": "productive_burn_btrack_research_only",
        "hypothesis_tag": "[HYPO]",
        "track_a_auto_merge": False,
        "lane_summaries": lane_summaries,
        "sandbox_jsonl_files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in jsonl_files],
        "sandbox_jsonl_rows": jsonl_rows,
        "bundle_path": "reports/sandbox/mkm_productive_burn_bundle_v1.json",
        "delegation_map": delegation.get("schema"),
        "credit_check_note": "Verify Billing credits 010B19-239742-DAF438 after 24-48h",
        "status": "in_progress" if not lane_summaries else "partial_or_complete",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "lanes": len(lane_summaries), "rows": jsonl_rows}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
