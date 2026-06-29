#!/usr/bin/env python3
"""Route ②: must_keep tier ablation on en_tech stress lane (B-track, research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comp_graphrag_philosophy_compression_sweep_v1 import BASE_MUST_KEEP  # noqa: E402
from scripts.compression_profile_v1 import profile_evaluate_report_kwargs  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_universal_compression_bench_matrix_sweep_v1 import (  # noqa: E402
    FORBIDDEN,
    MATRIX_INPUT,
    _base_eval_kwargs,
    _metrics,
)

LANE_ID = "en_tech_spec_stress_v1"
SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v2"
LANE_OVERRIDES = ROOT / "docs/final/artifacts/router_lane_shard_overrides_v1.json"
DOMAIN_FLOORS = {"en_tech_spec_stress": None}
OUT = ROOT / "reports/constitution/btrack_pilot/comp_universal_matrix_must_keep_tier_ablation_v1.json"

TIERS: dict[str, set[str]] = {
    "tier_0_empty": set(),
    "tier_1_base": set(BASE_MUST_KEEP),
    "tier_2_base_plus_domain": set(BASE_MUST_KEEP)
    | {"API", "HTTP", "JSON", "schema", "version", "compatible", "deprecated"},
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval(case: dict[str, Any], tier: str, must_keep: set[str], lane_overrides: dict[str, str]) -> dict[str, Any]:
    src = {"schema": "multilens_performance_eval_input_v1", "compression_cases": [case]}
    kw = _base_eval_kwargs()
    kw.update(profile_evaluate_report_kwargs("stress_bench"))
    report = evaluate_report(
        src,
        must_keep=must_keep,
        graph_wire_selective_bridge=False,
        emit_semantic_pointer=True,
        shards_root=SHARDS,
        lane_id_shard_overrides=lane_overrides,
        domain_min_saving_floor_overrides=DOMAIN_FLOORS,
        **kw,
    )
    m = _metrics(report)
    m["must_keep_tier"] = tier
    m["must_keep_count"] = len(must_keep)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-id", default=LANE_ID)
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    doc = json.loads(MATRIX_INPUT.read_text(encoding="utf-8-sig"))
    cases = [c for c in (doc.get("compression_cases") or []) if str(c.get("lane_id") or "") == args.lane_id]
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    odoc = json.loads(LANE_OVERRIDES.read_text(encoding="utf-8-sig"))
    lane_overrides = {str(k): str(v) for k, v in (odoc.get("overrides_by_lane_id") or {}).items()}

    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in TIERS}
    for case in cases:
        for tier, mk in TIERS.items():
            by_tier[tier].append(
                {
                    "case_id": case.get("id"),
                    "tier": tier,
                    "metrics": _eval(case, tier, mk, lane_overrides),
                }
            )

    def _agg(tier: str) -> dict[str, Any]:
        rows = by_tier[tier]
        js = [float(r["metrics"]["avg_reconstruction_fidelity_jaccard"]) for r in rows]
        sv = [float(r["metrics"]["global_token_saving_rate"]) for r in rows]
        si = [float(r["metrics"].get("avg_sensitive_integrity") or 0.0) for r in rows]
        return {
            "case_count": len(rows),
            "must_keep_count": len(TIERS[tier]),
            "jaccard_mean": sum(js) / len(js) if js else 0.0,
            "jaccard_min": min(js) if js else 0.0,
            "saving_mean": sum(sv) / len(sv) if sv else 0.0,
            "sensitive_integrity_mean": sum(si) / len(si) if si else 0.0,
            "below_0_85_count": sum(1 for j in js if j < 0.85),
        }

    baseline_agg = _agg("tier_1_base")
    deltas = {}
    for tier in TIERS:
        a = _agg(tier)
        deltas[tier] = {
            "delta_jaccard_mean_vs_tier_1": round(a["jaccard_mean"] - baseline_agg["jaccard_mean"], 6),
            "delta_jaccard_min_vs_tier_1": round(a["jaccard_min"] - baseline_agg["jaccard_min"], 6),
            "delta_saving_mean_vs_tier_1": round(a["saving_mean"] - baseline_agg["saving_mean"], 6),
        }

    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out_doc = {
        "schema": "comp_universal_matrix_must_keep_tier_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lane_id": args.lane_id,
        "compression_profile": "stress_bench",
        "tiers": {t: sorted(TIERS[t]) for t in TIERS},
        "aggregate_by_tier": {t: _agg(t) for t in TIERS},
        "delta_vs_tier_1_base": deltas,
        "track_a_active_written": False,
        "forbidden_write_path": str(FORBIDDEN.relative_to(ROOT)).replace("\\", "/"),
        "note": "Route ② — must_keep tier only; not router shard promotion.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"), "case_count": len(cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
