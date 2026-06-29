#!/usr/bin/env python3
"""Weekly LTM ops gate bundle — inject contract + bench 2/3 + P5 closure ([HYPO]).

  py scripts/check_ltm_weekly_ops_gate_v1.py
  py scripts/check_ltm_weekly_ops_gate_v1.py --skip-p5-closure
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

from mkm_ltm_lane_purity_lib_v1 import load_inject_contract  # noqa: E402
from mkm_ops_memory_index_lib_v1 import LANE_OPS_PACKS  # noqa: E402

DEFAULT_CONTRACT = SCRIPT_ROOT / "docs/final/artifacts/mkm_ltm_inject_contract_v1.json"
DEFAULT_BENCH_OUT = SCRIPT_ROOT / "reports/mkm_ltm_route_accuracy_bench_v1_latest.json"


def _run_py(root: Path, rel: str, *extra: str) -> tuple[int, str]:
    cmd = [sys.executable, str(root / rel), *extra]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    tail = ((proc.stderr or "") + (proc.stdout or ""))[-1200:]
    return proc.returncode, tail


def verify_inject_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lane_pack = contract.get("lane_ops_pack") or {}
    max_nodes = lane_pack.get("max_nodes_per_lane")
    if max_nodes != 4:
        errors.append(f"lane_ops_pack.max_nodes_per_lane expected 4 got {max_nodes!r}")
    for lane, pack in LANE_OPS_PACKS.items():
        if len(pack) > int(max_nodes or 4):
            errors.append(f"LANE_OPS_PACKS[{lane}] has {len(pack)} nodes > {max_nodes}")
    slice_cfg = contract.get("slice") or {}
    if slice_cfg.get("default_max_chars") != 1200:
        errors.append("slice.default_max_chars != 1200")
    ltm = contract.get("ltm_routing") or {}
    if ltm.get("max_ltm_concepts") != 5:
        errors.append("ltm_routing.max_ltm_concepts != 5")
    purity = contract.get("purity") or {}
    if purity.get("strict_exit_on_violation") is not True:
        errors.append("purity.strict_exit_on_violation != true")
    return errors


def verify_bench_report(
    path: Path,
    *,
    min_top1: float = 0.75,
    min_lane: float = 0.85,
    min_delta: float = 0.0,
    min_graph_only_hits: int = 1,
) -> list[str]:
    if not path.is_file():
        return [f"missing bench report: {path}"]
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") or {}
    top1 = float(agg.get("graph_top1_hit_rate") or 0)
    if top1 < min_top1:
        return [f"graph_top1_hit_rate {top1} < {min_top1}"]
    lane_rate = agg.get("lane_hit_rate")
    if lane_rate is not None and float(lane_rate) < min_lane:
        return [f"lane_hit_rate {lane_rate} < {min_lane}"]
    delta = float(agg.get("delta_graph_minus_blind") or 0)
    if delta < min_delta:
        return [f"delta_graph_minus_blind {delta} < {min_delta}"]
    graph_only = int(agg.get("graph_only_hit_count") or 0)
    if graph_only < min_graph_only_hits:
        return [f"graph_only_hit_count {graph_only} < {min_graph_only_hits}"]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--skip-route-bench", action="store_true")
    ap.add_argument("--skip-lane-purity", action="store_true")
    ap.add_argument("--skip-p5-closure", action="store_true")
    ap.add_argument("--min-graph-top1", type=float, default=0.75)
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    errors: list[str] = []

    try:
        contract = load_inject_contract(args.contract.resolve())
    except (OSError, ValueError) as exc:
        print(f"FAIL: contract: {exc}", file=sys.stderr)
        return 1

    errors.extend(verify_inject_contract(contract))

    if not args.skip_lane_purity:
        code, tail = _run_py(root, "scripts/check_mkm_ltm_lane_purity_v1.py")
        if code != 0:
            errors.append(f"lane_purity exit {code}: {tail}")

    if not args.skip_route_bench:
        code, tail = _run_py(root, "scripts/bench_mkm_ltm_route_accuracy_v1.py")
        if code != 0:
            errors.append(f"route_bench exit {code}: {tail}")
        else:
            errors.extend(
                verify_bench_report(
                    root / DEFAULT_BENCH_OUT.relative_to(SCRIPT_ROOT),
                    min_top1=args.min_graph_top1,
                )
            )

    if not args.skip_p5_closure:
        code, tail = _run_py(root, "scripts/check_ltm_p5_a2a_bridge_closure_v1.py")
        if code != 0:
            errors.append(f"p5_closure exit {code}: {tail}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(
        "ltm_weekly_ops_gate_v1: OK "
        f"contract={args.contract.name} lanes={len(LANE_OPS_PACKS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
