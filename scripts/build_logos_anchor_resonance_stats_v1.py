#!/usr/bin/env python3
"""Resonance / harmony-skew stats for Logos cosmic anchor batch (dual-gate).

Reproducible:
  py scripts/build_logos_anchor_resonance_stats_v1.py

Outputs:
  docs/final/artifacts/logos_anchor_resonance_stats_latest.json (production)
  docs/final/artifacts/logos_anchor_resonance_stats_sandbox_latest.json (sandbox)
  docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json (combined gates)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
SANDBOX_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_sandbox_v1"
OUT_PROD = ROOT / "docs/final/artifacts/logos_anchor_resonance_stats_latest.json"
OUT_SANDBOX = ROOT / "docs/final/artifacts/logos_anchor_resonance_stats_sandbox_latest.json"
OUT_DUAL = ROOT / "docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json"

PRIMITIVE_IDS = ("pathology", "circulation", "survival", "harmony", "valence")

HARMONY_SHARE_MAX = 0.65
MEAN_SPREAD_MIN_PRODUCTION = 0.08
MEAN_SPREAD_MIN_SANDBOX = 0.08


def _spread_4d(vector: dict[str, float]) -> float:
    vals = [float(vector[k]) for k in ("S", "L", "K", "M")]
    return max(vals) - min(vals)


def _top1(row: dict[str, Any]) -> str | None:
    align = row.get("kernel_alignment") or []
    if not align:
        return None
    top = align[0].get("primitive") or align[0].get("primitive_id")
    return str(top) if top is not None else None


def build_stats(
    *,
    batch_dir: Path,
    bridge_layer: str,
    recipe_id: str,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict[str, Any]] = []
    for path in sorted(batch_dir.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))

    top1_counts: dict[str, int] = {p: 0 for p in PRIMITIVE_IDS}
    per_anchor: list[dict[str, Any]] = []
    spreads: list[float] = []
    harmony_top1_similarities: list[float] = []
    non_harmony_top1_similarities: list[float] = []

    for row in rows:
        aid = row.get("anchor_id")
        v4 = row.get("vector_4d") or {}
        spread = _spread_4d(v4)
        spreads.append(spread)
        top = _top1(row)
        if top in top1_counts:
            top1_counts[top] += 1
        align = row.get("kernel_alignment") or []
        top_sim = float(align[0].get("similarity", 0)) if align else 0.0
        if top == "harmony":
            harmony_top1_similarities.append(top_sim)
        elif top:
            non_harmony_top1_similarities.append(top_sim)
        per_anchor.append(
            {
                "anchor_id": aid,
                "top1_primitive_id": top,
                "top1_similarity": round(top_sim, 6),
                "spread_4d": round(spread, 6),
                "vector_4d": {k: round(float(v4[k]), 6) for k in ("S", "L", "K", "M")},
            }
        )

    n = max(1, len(rows))
    harmony_share = top1_counts.get("harmony", 0) / n
    mean_spread = statistics.mean(spreads) if spreads else 0.0
    stdev_spread = statistics.pstdev(spreads) if len(spreads) > 1 else 0.0
    spread_min = MEAN_SPREAD_MIN_SANDBOX if bridge_layer == "sandbox" else MEAN_SPREAD_MIN_PRODUCTION

    gate_ranking = {
        "gate_id": "ranking_skew",
        "harmony_top1_share": round(harmony_share, 4),
        "harmony_share_max": HARMONY_SHARE_MAX,
        "pass": harmony_share <= HARMONY_SHARE_MAX,
    }
    gate_geometry = {
        "gate_id": "geometric_spread",
        "bridge_layer": bridge_layer,
        "recipe_id": recipe_id,
        "mean_spread_4d": round(mean_spread, 6),
        "mean_spread_4d_min": spread_min,
        "pass": mean_spread >= spread_min,
    }

    summary = {
        "harmony_top1_share": round(harmony_share, 4),
        "harmony_top1_count": top1_counts.get("harmony", 0),
        "anchor_count": len(rows),
        "diversity_index_1_minus_harmony_share": round(1.0 - harmony_share, 4),
        "mean_spread_4d": round(mean_spread, 6),
        "stdev_spread_4d": round(stdev_spread, 6),
        "top1_primitive_histogram": top1_counts,
        "mean_top1_similarity_when_harmony": round(
            statistics.mean(harmony_top1_similarities) if harmony_top1_similarities else 0.0,
            6,
        ),
        "mean_top1_similarity_when_non_harmony": round(
            statistics.mean(non_harmony_top1_similarities)
            if non_harmony_top1_similarities
            else 0.0,
            6,
        ),
        "gate_ranking": gate_ranking,
        "gate_geometry": gate_geometry,
        "skew_mitigation_gate": {
            "harmony_share_max_recommended": HARMONY_SHARE_MAX,
            "mean_spread_4d_min_recommended": spread_min,
            "harmony_share_within_gate": gate_ranking["pass"],
            "mean_spread_within_gate": gate_geometry["pass"],
        },
    }

    return {
        "schema": "logos_anchor_resonance_stats_v1",
        "version": "1.1.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "bridge_layer": bridge_layer,
        "recipe_id": recipe_id,
        "batch_dir": batch_dir.relative_to(ROOT).as_posix(),
        "summary": summary,
        "per_anchor": per_anchor,
        "reproducible_command": "py scripts/build_logos_anchor_resonance_stats_v1.py",
        "notes_ko": (
            "Gate A=ranking_skew(harmony share). Gate B=geometric_spread(mean_spread_4d). "
            "production bridge는 구조적으로 spread 낮음 — sandbox layer 별도 관측."
        ),
    }


def build_dual_gate_report(
    prod_stats: dict[str, Any],
    sandbox_stats: dict[str, Any],
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prod_g = prod_stats["summary"]["gate_geometry"]
    prod_r = prod_stats["summary"]["gate_ranking"]
    sand_g = sandbox_stats["summary"]["gate_geometry"]
    return {
        "schema": "logos_anchor_resonance_dual_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "gates": {
            "gate_a_ranking_production": prod_r,
            "gate_b_geometry_production": prod_g,
            "gate_b_prime_geometry_sandbox": sand_g,
        },
        "wave25_pass": {
            "ranking_production": prod_r["pass"],
            "geometry_sandbox": sand_g["pass"],
            "all_research_gates": prod_r["pass"] and sand_g["pass"],
        },
        "reproducible_command": "py scripts/run_logos_spread_tuning_chain_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=BATCH_DIR)
    parser.add_argument("--sandbox-dir", type=Path, default=SANDBOX_DIR)
    args = parser.parse_args()
    if not args.batch_dir.is_dir():
        print(f"ERROR: batch dir missing: {args.batch_dir}", file=sys.stderr)
        return 1

    prod = build_stats(
        batch_dir=args.batch_dir,
        bridge_layer="production",
        recipe_id="gematria_bridge_v1",
    )
    OUT_PROD.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROD.write_text(json.dumps(prod, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_PROD}")

    if args.sandbox_dir.is_dir():
        sandbox = build_stats(
            batch_dir=args.sandbox_dir,
            bridge_layer="sandbox",
            recipe_id="gematria_bridge_sandbox_v1",
        )
        OUT_SANDBOX.write_text(
            json.dumps(sandbox, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        dual = build_dual_gate_report(prod, sandbox)
        OUT_DUAL.write_text(json.dumps(dual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT_SANDBOX}")
        print(f"WROTE: {OUT_DUAL}")
        sg = sandbox["summary"]
        dg = dual["wave25_pass"]
        print(
            f"  prod harmony_share={prod['summary']['harmony_top1_share']} "
            f"sandbox mean_spread={sg['mean_spread_4d']}"
        )
        print(
            f"  gate_a={dg['ranking_production']} "
            f"gate_b_prime={dg['geometry_sandbox']} "
            f"all_research={dg['all_research_gates']}"
        )
    else:
        print(f"SKIP sandbox: {args.sandbox_dir} missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
