#!/usr/bin/env python3
"""Compare two matrix sweeps per lane (B-track AB); delta Jaccard min/mean vs baseline."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = (
    ROOT / "reports/constitution/btrack_pilot/baselines/router_tuning_v1"
    / "comp_universal_bench_matrix_sweep_baseline_frozen.json"
)
OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_matrix_router_ab_by_lane_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _lane_agg(rows: list[dict[str, Any]], profile: str = "economy_plus_wire") -> dict[str, dict[str, float]]:
    by_lane: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        lid = str(r.get("lane_id") or "")
        j = (r.get(profile) or {}).get("avg_reconstruction_fidelity_jaccard")
        if j is not None:
            by_lane[lid].append(float(j))
    out: dict[str, dict[str, float]] = {}
    for lid, vals in by_lane.items():
        below_85 = sum(1 for v in vals if v < 0.85)
        out[lid] = {
            "case_count": len(vals),
            "jaccard_mean": sum(vals) / len(vals),
            "jaccard_min": min(vals),
            "below_floor_0_85_count": below_85,
            "below_floor_0_85_rate": below_85 / len(vals) if vals else 0.0,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-json", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--candidate-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--jaccard-floor", type=float, default=0.85)
    args = ap.parse_args()

    base_doc = json.loads(args.baseline_json.read_text(encoding="utf-8-sig"))
    cand_doc = json.loads(args.candidate_json.read_text(encoding="utf-8-sig"))
    base_rows = list(base_doc.get("rows") or [])
    cand_rows = list(cand_doc.get("rows") or [])

    include = set(cand_doc.get("include_lane_ids") or [])
    if include:
        base_rows = [r for r in base_rows if str(r.get("lane_id") or "") in include]
        cand_rows = [r for r in cand_rows if str(r.get("lane_id") or "") in include]

    base_lanes = _lane_agg(base_rows)
    cand_lanes = _lane_agg(cand_rows)

    comparison: dict[str, Any] = {}
    for lid in sorted(set(base_lanes) | set(cand_lanes)):
        b = base_lanes.get(lid, {})
        c = cand_lanes.get(lid, {})
        delta_mean = None
        delta_min = None
        if b and c:
            delta_mean = round(c["jaccard_mean"] - b["jaccard_mean"], 6)
            delta_min = round(c["jaccard_min"] - b["jaccard_min"], 6)
        comparison[lid] = {
            "baseline": b,
            "candidate": c,
            "delta_jaccard_mean": delta_mean,
            "delta_jaccard_min": delta_min,
            "candidate_passes_lane_min_floor": bool(c.get("jaccard_min", 0) >= args.jaccard_floor),
        }

    out_doc = {
        "schema": "comp_universal_matrix_router_ab_by_lane_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "jaccard_floor": args.jaccard_floor,
        "baseline_sweep": _rel(args.baseline_json),
        "candidate_sweep": _rel(args.candidate_json),
        "candidate_router_variant": cand_doc.get("router_variant"),
        "lanes": comparison,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
