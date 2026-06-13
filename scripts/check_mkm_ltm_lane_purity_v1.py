#!/usr/bin/env python3
"""Strict lane resume pack purity gate ([HYPO] / B-track).

  py scripts/check_mkm_ltm_lane_purity_v1.py
  py scripts/check_mkm_ltm_lane_purity_v1.py --lane ms
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_ltm_lane_purity_lib_v1 import (  # noqa: E402
    check_all_lanes_purity,
    load_inject_contract,
)
from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    LANE_OPS_PACKS,
    load_index,
    nodes_for_resume,
)

DEFAULT_CONTRACT = SCRIPT_ROOT / "docs" / "final" / "artifacts" / "mkm_ltm_inject_contract_v1.json"


def _lane_inject_text(root: Path, lane: str) -> str:
    index = load_index(DEFAULT_INDEX_PATH)
    lines: list[str] = []
    for _node_id, node in nodes_for_resume(index, lane=lane, root=root):
        lines.append(node.get("essence") or "")
        for tag in node.get("must_keep_tags") or []:
            lines.append(str(tag))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument(
        "--lane",
        choices=sorted(LANE_OPS_PACKS.keys()),
        action="append",
        default=[],
        help="Check one lane (repeatable). Default: all lanes.",
    )
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    if not DEFAULT_INDEX_PATH.is_file():
        print("FAIL: ops index missing — run build_mkm_ops_memory_index_v1.py", file=sys.stderr)
        return 1

    try:
        contract = load_inject_contract(args.contract)
    except (OSError, ValueError) as exc:
        print(f"FAIL: contract: {exc}", file=sys.stderr)
        return 1

    lanes = args.lane or sorted(LANE_OPS_PACKS.keys())
    lane_texts: dict[str, str] = {}
    for lane in lanes:
        try:
            lane_texts[lane] = _lane_inject_text(root, lane)
        except (KeyError, ValueError, FileNotFoundError) as exc:
            print(f"FAIL: lane {lane}: {exc}", file=sys.stderr)
            return 1

    errors = check_all_lanes_purity(lane_texts, contract=contract)
    if errors:
        for err in errors:
            print(f"FAIL: purity: {err}", file=sys.stderr)
        return 1

    print(f"lane_purity: OK ({len(lanes)} lanes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
