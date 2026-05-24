#!/usr/bin/env python3
"""Summarize golden_core vs blended Jaccard per expansion pool (lane isolation, B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports/golden40_expansion_lane_isolation_summary_v1_latest.json"

ARTIFACTS: dict[str, Path] = {
    "mixed_matrix": ROOT / "reports/golden_40_expansion_dryrun_rq021_mixed_v1_latest.json",
    "homogeneous_full": ROOT / "reports/golden_40_expansion_dryrun_rq021_homogeneous_full_v1_latest.json",
    "homogeneous_sasang_ko": ROOT / "reports/golden_40_expansion_dryrun_rq021_sasang_v1_latest.json",
    "homogeneous_logos_verse": ROOT / "reports/golden_40_expansion_dryrun_rq021_logos_v1_latest.json",
    "golden_core_only": ROOT / "reports/golden_40_expansion_dryrun_rq021_golden_core_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _n400_row(doc: dict[str, Any]) -> dict[str, Any] | None:
    for tier in doc.get("tiers") or []:
        if int(tier.get("target_case_count") or 0) == 400:
            agg = tier.get("aggregate_metrics") or {}
            gc = tier.get("golden_core_only_metrics") or {}
            return {
                "actual": tier.get("actual_case_count"),
                "max_pool": tier.get("max_available_in_pool"),
                "blended_jaccard": agg.get("avg_reconstruction_fidelity_jaccard"),
                "golden_core_jaccard": gc.get("avg_reconstruction_fidelity_jaccard"),
                "blended_floor_ok": tier.get("floor_regression_ok"),
                "golden_core_floor_ok": (tier.get("golden_core_verdict") or {}).get("floor_regression_ok"),
                "expansion_dilution": bool(
                    (tier.get("golden_core_verdict") or {}).get("floor_regression_ok")
                    and not tier.get("floor_regression_ok")
                ),
                "delta_jaccard_pp": round(
                    ((agg.get("avg_reconstruction_fidelity_jaccard") or 0) - (gc.get("avg_reconstruction_fidelity_jaccard") or 0))
                    * 100.0,
                    2,
                )
                if gc
                else None,
            }
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pools: dict[str, Any] = {}
    for mode, path in ARTIFACTS.items():
        doc = _load(path)
        if not doc:
            pools[mode] = {"artifact": str(path), "missing": True}
            continue
        pools[mode] = {
            "artifact": str(path.relative_to(ROOT)).replace("\\", "/"),
            "pool_mode": doc.get("pool_mode", mode),
            "expansion_dilution_observed": (doc.get("summary") or {}).get("expansion_dilution_observed"),
            "n400": _n400_row(doc),
        }

    dilution_modes = [m for m, p in pools.items() if isinstance(p, dict) and (p.get("n400") or {}).get("expansion_dilution")]
    gc_ref = (pools.get("golden_core_only") or {}).get("n400") or {}

    doc = {
        "schema": "golden40_expansion_lane_isolation_summary_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "golden_core_baseline_n400": gc_ref,
        "pools": pools,
        "verdict": {
            "expansion_dilution_modes": dilution_modes,
            "recommendation": (
                "Isolate expansion lanes from headline KPI; report golden_core + per-lane blended separately"
                if dilution_modes
                else "No dilution signal in loaded artifacts"
            ),
            "p4_gate_candidate": False,
            "promotion": "HOLD — FAIL-COMP-004; MS excluded",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out} dilution_modes={len(dilution_modes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
