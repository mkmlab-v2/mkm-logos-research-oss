#!/usr/bin/env python3
"""P4 LTM scale closure gate — trading guard subgraph + token bench regression ([HYPO]).

  py scripts/check_ltm_p4_scale_closure_v1.py
  py scripts/check_ltm_p4_scale_closure_v1.py --min-mean-savings-ratio 0.95
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
    CONCEPT_SPECS,
    build_graph_document,
    route_concepts_by_query,
    verify_graph_topology,
)
from mkm_long_term_memory_graph_topology_v1 import verify_topology_coverage  # noqa: E402

TRADING_GUARD_IDS = (
    "trading_go_nogo_status_ssot",
    "trading_human_execution_approval_gate",
    "vps_pm2_live_entry_boundary",
    "fact_safe_risk_sync_chain",
)
MIN_CONCEPT_COUNT = 54


def _load_bench(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--min-concept-count", type=int, default=MIN_CONCEPT_COUNT)
    ap.add_argument(
        "--min-mean-savings-ratio",
        type=float,
        default=0.95,
        help="Lane token bench aggregate gate (skip if bench JSON missing).",
    )
    ap.add_argument(
        "--bench-json",
        type=Path,
        default=SCRIPT_ROOT / "reports" / "mkm_ltm_resume_lane_token_bench_v1_latest.json",
    )
    ap.add_argument("--skip-bench", action="store_true")
    ap.add_argument("--skip-prism-report", action="store_true")
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    errors: list[str] = []

    count = len(CONCEPT_SPECS)
    if count < args.min_concept_count:
        errors.append(f"concept_count {count} < min {args.min_concept_count}")

    topo_errors = verify_topology_coverage(list(CONCEPT_BY_ID.keys()))
    errors.extend(topo_errors)

    for cid in TRADING_GUARD_IDS:
        if cid not in CONCEPT_BY_ID:
            errors.append(f"missing trading guard concept: {cid}")

    try:
        graph = build_graph_document(root)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"build_graph_document failed: {exc}")
        graph = {}

    if graph:
        errors.extend(verify_graph_topology(graph))
        routed = route_concepts_by_query(graph, "vps pm2 live trading go nogo human approval")
        ids = {cid for cid, _ in routed}
        if not ids.intersection(TRADING_GUARD_IDS):
            errors.append("trading guard subgraph not routable from composite query")

    if not args.skip_bench:
        bench_path = args.bench_json
        if not bench_path.is_file():
            proc = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts" / "bench_mkm_ltm_resume_lane_token_v1.py"),
                    "--out",
                    str(bench_path),
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                errors.append(
                    f"bench subprocess exit {proc.returncode}: {(proc.stderr or '')[-500:]}"
                )
        if bench_path.is_file():
            bench = _load_bench(bench_path)
            mean_ratio = float(
                (bench.get("aggregate") or {}).get("mean_savings_ratio") or 0.0
            )
            if mean_ratio < args.min_mean_savings_ratio:
                errors.append(
                    f"mean_savings_ratio {mean_ratio} < {args.min_mean_savings_ratio}"
                )

    if not args.skip_prism_report:
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "scripts" / "report_ltm_prism_id_gaps_v1.py"),
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append(f"prism gap report exit {proc.returncode}")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1

    print(
        f"ltm_p4_scale_closure_v1: OK concepts={count} "
        f"trading_guard={len(TRADING_GUARD_IDS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
