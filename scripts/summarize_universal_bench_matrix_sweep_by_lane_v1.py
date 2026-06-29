#!/usr/bin/env python3
"""Per-lane KPI from comp_universal_bench_matrix_sweep_v1.json + Jaccard floor gate (B-track)."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_v1.json"
DEFAULT_OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_by_lane_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {}
    return {
        "mean": sum(vals) / len(vals),
        "min": min(vals),
        "max": max(vals),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--jaccard-floor",
        type=float,
        default=0.85,
        help="Research observation threshold for per-case min Jaccard.",
    )
    ap.add_argument(
        "--profile",
        choices=("economy", "economy_plus_wire"),
        default="economy_plus_wire",
    )
    ap.add_argument(
        "--exclude-lane-id",
        action="append",
        default=[],
        help="Optional lanes to omit from operational rollup.",
    )
    args = ap.parse_args()

    in_path = (ROOT / args.in_json).resolve() if not args.in_json.is_absolute() else args.in_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    if not in_path.is_file():
        print(json.dumps({"error": "missing_sweep", "path": str(in_path)}, ensure_ascii=False))
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    exclude = set(args.exclude_lane_id or [])
    floor = float(args.jaccard_floor)
    prof = args.profile

    by_lane: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in doc.get("rows") or []:
        lid = str(row.get("lane_id") or "unknown")
        if lid in exclude:
            continue
        by_lane[lid].append(row)

    lane_rows: list[dict[str, Any]] = []
    all_j: list[float] = []
    all_s: list[float] = []
    below_floor_total = 0
    case_total = 0

    for lane_id in sorted(by_lane.keys()):
        rows = by_lane[lane_id]
        j_vals = [
            float(r[prof]["avg_reconstruction_fidelity_jaccard"])
            for r in rows
            if r.get(prof, {}).get("avg_reconstruction_fidelity_jaccard") is not None
        ]
        s_vals = [
            float(r[prof]["global_token_saving_rate"])
            for r in rows
            if r.get(prof, {}).get("global_token_saving_rate") is not None
        ]
        below = sum(1 for v in j_vals if v < floor)
        case_total += len(rows)
        below_floor_total += below
        all_j.extend(j_vals)
        all_s.extend(s_vals)
        js = _stats(j_vals)
        ss = _stats(s_vals)
        lane_pass = js.get("min", 0.0) >= floor if js else False
        lane_rows.append(
            {
                "lane_id": lane_id,
                "domain_tag": rows[0].get("domain_tag") if rows else None,
                "case_count": len(rows),
                "jaccard": js,
                "saving_rate": ss,
                "below_jaccard_floor_count": below,
                "jaccard_floor": floor,
                "lane_min_meets_floor": lane_pass,
            }
        )

    global_j = _stats(all_j)
    global_s = _stats(all_s)
    worst_lane_min = min((lr["jaccard"].get("min", 1.0) for lr in lane_rows if lr["jaccard"]), default=None)

    out = {
        "schema": "comp_universal_bench_matrix_sweep_by_lane_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "source_sweep": str(in_path.relative_to(ROOT)).replace("\\", "/"),
        "profile": prof,
        "jaccard_floor": floor,
        "excluded_lane_ids": sorted(exclude),
        "case_count": case_total,
        "lanes": lane_rows,
        "global_aggregate": {
            "jaccard": global_j,
            "saving_rate": global_s,
            "below_jaccard_floor_count": below_floor_total,
            "below_jaccard_floor_rate": (below_floor_total / case_total if case_total else None),
            "worst_lane_jaccard_min": worst_lane_min,
        },
        "floor_gate_research_only": {
            "all_lanes_min_meets_floor": all(
                lr.get("lane_min_meets_floor") for lr in lane_rows if lr.get("jaccard")
            ),
            "note": "Observation gate only — not Track A promotion or MS headline.",
        },
        "track_a_active_written": doc.get("track_a_active_written", False),
        "do_not_promote": [
            "Universal matrix B-track sweep — not Golden 40 or MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "case_count": case_total,
                "lane_count": len(lane_rows),
                "global_jaccard_mean": global_j.get("mean"),
                "below_floor_rate": out["global_aggregate"]["below_jaccard_floor_rate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
