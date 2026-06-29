#!/usr/bin/env python3
"""P5 LTM ↔ A2A bridge closure gate ([HYPO] / B-track · RQ-019).

  py scripts/check_ltm_p5_a2a_bridge_closure_v1.py
  py scripts/check_ltm_p5_a2a_bridge_closure_v1.py --run-encoding-smoke
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    CONCEPT_BY_ID,
    build_graph_document,
    route_concepts_by_query,
    verify_graph_topology,
)
from mkm_long_term_memory_graph_topology_v1 import verify_topology_coverage  # noqa: E402

A2A_BRIDGE_IDS = (
    "a2a_two_layer_architecture_ssot",
    "ltm_ops_inject_to_a2a_wire",
    "inter_agent_encoding_smoke_chain",
    "a2a_ltm_track_wall",
)
WALL = SCRIPT_ROOT / "docs/final/artifacts/ltm_a2a_bridge_wall_v1.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument(
        "--run-encoding-smoke",
        action="store_true",
        help="Run Invoke-MkmInterAgentEncodingSmoke_v1.ps1 (slow).",
    )
    ap.add_argument("--skip-bridge-map", action="store_true")
    ap.add_argument("--skip-p4-closure", action="store_true")
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    errors: list[str] = []

    if not WALL.is_file():
        errors.append(f"missing wall doc: {WALL}")
    else:
        wall = _read_json(WALL)
        if wall.get("schema") != "ltm_a2a_bridge_wall_v1":
            errors.append("ltm_a2a_bridge_wall_v1 schema mismatch")
        forbidden = wall.get("forbidden_auto_merge") or []
        if "live_trading_enable" not in forbidden:
            errors.append("wall missing live_trading_enable forbidden")

    for cid in A2A_BRIDGE_IDS:
        if cid not in CONCEPT_BY_ID:
            errors.append(f"missing a2a bridge concept: {cid}")

    errors.extend(verify_topology_coverage(list(CONCEPT_BY_ID.keys())))

    try:
        graph = build_graph_document(root)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"build_graph_document: {exc}")
        graph = {}

    if graph:
        errors.extend(verify_graph_topology(graph))
        routed = route_concepts_by_query(
            graph, "a2a inter agent ltm wire encoding rq019 track wall"
        )
        ids = {cid for cid, _ in routed}
        if not ids.intersection(A2A_BRIDGE_IDS):
            errors.append("a2a bridge concepts not routable from composite query")

    if not args.skip_bridge_map:
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "build_ltm_a2a_bridge_map_v1.py")],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append(f"build_ltm_a2a_bridge_map exit {proc.returncode}")

    if not args.skip_p4_closure:
        proc = subprocess.run(
            [sys.executable, str(root / "scripts" / "check_ltm_p4_scale_closure_v1.py")],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append(f"p4 closure regression exit {proc.returncode}")

    if args.run_encoding_smoke:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(root / "scripts" / "Invoke-MkmInterAgentEncodingSmoke_v1.ps1"),
                "-SkipDialogueMock",
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-800:]
            errors.append(f"encoding smoke exit {proc.returncode}: {tail}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(
        f"ltm_p5_a2a_bridge_closure_v1: OK "
        f"concepts={len(CONCEPT_BY_ID)} a2a_bridge={len(A2A_BRIDGE_IDS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
