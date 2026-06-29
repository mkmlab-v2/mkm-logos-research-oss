#!/usr/bin/env python3
"""en_tech_spec_stress_v1 only: profile matrix on v2 shards (B-track, research_only)."""

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
from scripts.compression_profile_v1 import CompressionProfile, profile_evaluate_report_kwargs  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402
from scripts.run_universal_compression_bench_matrix_sweep_v1 import (  # noqa: E402
    FORBIDDEN,
    MATRIX_INPUT,
    _base_eval_kwargs,
    _metrics,
)

LANE_ID = "en_tech_spec_stress_v1"
DEFAULT_PROFILES: tuple[CompressionProfile, ...] = (
    "economy",
    "stress_bench",
    "fidelity",
    "literal",
)
OUT = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_stress_profile_matrix_v1.json"
SHARDS = ROOT / "codebook" / "shards_btrack_router_sharp_v2"
LANE_OVERRIDES = ROOT / "docs/final/artifacts/router_lane_shard_overrides_v1.json"
DOMAIN_FLOORS = {"en_tech_spec_stress": None}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval(
    case: dict[str, Any],
    profile: CompressionProfile,
    *,
    shards_root: Path,
    lane_overrides: dict[str, str],
) -> dict[str, Any]:
    src = {"schema": "multilens_performance_eval_input_v1", "compression_cases": [case]}
    kw = _base_eval_kwargs()
    prof = profile_evaluate_report_kwargs(profile)
    kw.update(prof)
    report = evaluate_report(
        src,
        must_keep=set(BASE_MUST_KEEP),
        graph_wire_selective_bridge=False,
        emit_semantic_pointer=True,
        shards_root=shards_root,
        lane_id_shard_overrides=lane_overrides,
        domain_min_saving_floor_overrides=DOMAIN_FLOORS,
        **kw,
    )
    return _metrics(report)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-id", default=LANE_ID)
    ap.add_argument("--profiles", default=",".join(DEFAULT_PROFILES))
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    profiles: list[CompressionProfile] = [p.strip() for p in args.profiles.split(",") if p.strip()]  # type: ignore[misc]
    doc = json.loads(MATRIX_INPUT.read_text(encoding="utf-8-sig"))
    cases = [c for c in (doc.get("compression_cases") or []) if str(c.get("lane_id") or "") == args.lane_id]
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    odoc = json.loads(LANE_OVERRIDES.read_text(encoding="utf-8-sig"))
    lane_overrides = {str(k): str(v) for k, v in (odoc.get("overrides_by_lane_id") or {}).items()}

    cells: dict[str, list[dict[str, Any]]] = {p: [] for p in profiles}
    for case in cases:
        for profile in profiles:
            m = _eval(case, profile, shards_root=SHARDS, lane_overrides=lane_overrides)
            cells[profile].append(
                {
                    "case_id": case.get("id"),
                    "compression_profile": profile,
                    "metrics": m,
                }
            )

    def _agg(profile: str) -> dict[str, Any]:
        rows = cells[profile]
        js = [float(r["metrics"]["avg_reconstruction_fidelity_jaccard"]) for r in rows]
        sv = [float(r["metrics"]["global_token_saving_rate"]) for r in rows]
        return {
            "case_count": len(rows),
            "jaccard_mean": sum(js) / len(js) if js else 0.0,
            "jaccard_min": min(js) if js else 0.0,
            "jaccard_max": max(js) if js else 0.0,
            "saving_mean": sum(sv) / len(sv) if sv else 0.0,
            "below_0_85_count": sum(1 for j in js if j < 0.85),
        }

    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out_doc = {
        "schema": "comp_en_tech_stress_profile_matrix_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "lane_id": args.lane_id,
        "profiles": profiles,
        "shards_root": "codebook/shards_btrack_router_sharp_v2",
        "domain_min_saving_floor_overrides": DOMAIN_FLOORS,
        "aggregate_by_profile": {p: _agg(p) for p in profiles},
        "track_a_active_written": False,
        "forbidden_write_path": str(FORBIDDEN.relative_to(ROOT)).replace("\\", "/"),
        "per_case_by_profile": cells,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"), "case_count": len(cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
