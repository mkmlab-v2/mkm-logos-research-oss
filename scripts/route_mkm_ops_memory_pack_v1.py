#!/usr/bin/env python3
"""Route ops memory lane pack from topic text ([HYPO] / B-track).

  py scripts/route_mkm_ops_memory_pack_v1.py --topic "Nebius 잔액 web_ops"
  py scripts/route_mkm_ops_memory_pack_v1.py --topic "GPU infra" --build-resume-pack
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    LANE_OPS_PACKS,
    load_index,
    nodes_for_resume,
    resolve_lane_from_topic,
    route_nodes_by_field_tags,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic", required=True, help="Free-text topic for lane/node routing.")
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument(
        "--build-resume-pack",
        action="store_true",
        help="Invoke build_mkm_chat_resume_pack_v1.py with resolved --lane.",
    )
    ap.add_argument("--include-slice", action="store_true")
    ap.add_argument(
        "--repair-v2-slice",
        action="store_true",
        help="Pass --repair-v2-slice to resume pack (noise-guard slices).",
    )
    ap.add_argument("--slice-max-chars", type=int, default=800)
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    try:
        index = load_index(args.index)
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    lane = resolve_lane_from_topic(args.topic)
    routed = route_nodes_by_field_tags(index, args.topic)
    pack_nodes: list[str] = []
    if lane and lane in LANE_OPS_PACKS:
        try:
            pack_nodes = [nid for nid, _ in nodes_for_resume(index, lane=lane)]
        except (KeyError, ValueError):
            pack_nodes = []

    out = {
        "ok": True,
        "schema": "mkm_ops_memory_route_v1",
        "research_only": True,
        "topic": args.topic,
        "resolved_lane": lane,
        "lane_pack_node_ids": pack_nodes,
        "field_tag_routed_node_ids": [nid for nid, _ in routed],
        "recommended_command": (
            f"py scripts/build_mkm_chat_resume_pack_v1.py --lane {lane}"
            if lane
            else "py scripts/build_mkm_chat_resume_pack_v1.py"
        ),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.build_resume_pack and lane:
        cmd = [
            sys.executable,
            str(root / "scripts" / "build_mkm_chat_resume_pack_v1.py"),
            "--lane",
            lane,
        ]
        if args.repair_v2_slice:
            cmd.append("--repair-v2-slice")
        elif args.include_slice:
            cmd.append("--include-slice")
        if args.repair_v2_slice or args.include_slice:
            cmd.extend(["--slice-max-chars", str(args.slice_max_chars)])
        cmd.extend(["--topic", args.topic])
        return subprocess.run(cmd, cwd=str(root)).returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
