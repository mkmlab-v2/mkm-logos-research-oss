#!/usr/bin/env python3
"""Build reports/multi_res_todo_index_v1_latest.json — 3-layer todo coordinate index.

[HYPO] / research_only / B-track — does NOT enqueue todo_queue_v1.

  py scripts/build_multi_res_todo_index_v1.py
  py scripts/build_multi_res_todo_index_v1.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from multi_res_todo_index_lib_v1 import build_todo_index_document

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = SCRIPT_ROOT / "reports/multi_res_todo_index_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", help="Validate build only; do not write JSON.")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    mission_log = root / "MISSION_LOG.md"
    if not mission_log.is_file():
        print(f"FAIL: MISSION_LOG.md missing at {mission_log}", file=sys.stderr)
        print("Local-only SSOT (gitignored) — fail-fast.", file=sys.stderr)
        return 1

    doc = build_todo_index_document(root)
    n_low = doc["meta"]["n_low_res"]
    if n_low < 1:
        print("FAIL: no lane_actions extracted from MISSION_LOG", file=sys.stderr)
        return 1

    if args.dry_run:
        print(
            f"DRY-RUN OK: low={n_low} mid={doc['meta']['n_mid_res']} "
            f"high={doc['meta']['n_high_res']}"
        )
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"OK: lane_actions={n_low} checkpoints={len(doc['mid_res']['checkpoints'])} "
        f"delegation_pending={len(doc['mid_res']['delegation_pending'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
